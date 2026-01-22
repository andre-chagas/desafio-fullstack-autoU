import os
import io
import re
import json
from collections import Counter
from typing import Dict, Iterable, Optional, Tuple

from flask import Flask, jsonify, render_template, request
from werkzeug.utils import secure_filename
from PyPDF2 import PdfReader
import requests


app = Flask(__name__)


STOPWORDS = {
    "a",
    "ainda",
    "alem",
    "ao",
    "aos",
    "até",
    "com",
    "como",
    "da",
    "das",
    "de",
    "dela",
    "dele",
    "deles",
    "depois",
    "do",
    "dos",
    "e",
    "ela",
    "ele",
    "eles",
    "em",
    "entre",
    "era",
    "esse",
    "esta",
    "está",
    "está",
    "estao",
    "estão",
    "eu",
    "foi",
    "for",
    "houve",
    "ja",
    "já",
    "la",
    "lá",
    "lhe",
    "lhés",
    "lhes",
    "lo",
    "mais",
    "mas",
    "me",
    "mesmo",
    "meu",
    "minha",
    "na",
    "nas",
    "nao",
    "não",
    "nas",
    "nem",
    "no",
    "nos",
    "nós",
    "nosso",
    "nossa",
    "o",
    "os",
    "ou",
    "para",
    "pela",
    "pelas",
    "pelo",
    "pelos",
    "por",
    "porque",
    "que",
    "quem",
    "se",
    "seu",
    "seus",
    "sob",
    "sobre",
    "sua",
    "suas",
    "também",
    "te",
    "tem",
    "têm",
    "tenho",
    "teu",
    "tua",
    "um",
    "uma",
    "você",
    "vocês",
    "vos",
    "your",
    "you",
    "the",
    "and",
    "is",
    "are",
    "to",
    "of",
    "in",
    "for",
    "on",
    "with",
}


PRODUTIVO_KEYWORDS = {
    "suporte",
    "erro",
    "problema",
    "falha",
    "chamado",
    "ticket",
    "incidente",
    "atualização",
    "atualizacao",
    "status",
    "andamento",
    "reclamação",
    "reclamacao",
    "cancelamento",
    "contrato",
    "pagamento",
    "fatura",
    "boleto",
    "limite",
    "cartão",
    "cartao",
    "acesso",
    "login",
    "senha",
    "cadastro",
    "duvida",
    "dúvida",
    "solicito",
    "solicitação",
    "solicitacao",
}


IMPRODUTIVO_KEYWORDS = {
    "feliz natal",
    "feliz páscoa",
    "feliz pascoa",
    "feliz ano novo",
    "boas festas",
    "parabéns",
    "parabens",
    "agradeço",
    "agradeco",
    "obrigado",
    "obrigada",
    "bom dia",
    "boa tarde",
    "boa noite",
    "abraços",
    "abçs",
    "att.",
}


HF_API_TOKEN = os.getenv("HF_API_TOKEN")
HF_CLASSIFICATION_MODEL = os.getenv(
    "HF_CLASSIFICATION_MODEL", "facebook/bart-large-mnli"
)
HF_GENERATION_MODEL = os.getenv("HF_GENERATION_MODEL", "gpt2")


TRAINING_PATH = os.path.join(os.path.dirname(__file__), "training_data.json")


def preprocess_text(text: str) -> str:
    lowered = text.lower()
    tokens = re.findall(r"\b\w+\b", lowered, flags=re.UNICODE)
    filtered = [t for t in tokens if t not in STOPWORDS and len(t) > 2]
    return " ".join(filtered)


def load_training_examples(path: str) -> Dict[str, Iterable[str]]:
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return {}
        return {str(label): list(texts) for label, texts in data.items()}
    except Exception:
        return {}


def extend_keywords_from_training() -> None:
    data = load_training_examples(TRAINING_PATH)
    if not data:
        return
    productive_examples = data.get("Produtivo", []) or data.get("produtivo", [])
    unproductive_examples = data.get("Improdutivo", []) or data.get("improdutivo", [])
    if productive_examples:
        tokens = []
        for text in productive_examples:
            processed = preprocess_text(text)
            tokens.extend(processed.split())
        counts = Counter(tokens)
        for token, _ in counts.most_common(25):
            PRODUTIVO_KEYWORDS.add(token)
    if unproductive_examples:
        tokens = []
        for text in unproductive_examples:
            processed = preprocess_text(text)
            tokens.extend(processed.split())
        counts = Counter(tokens)
        for token, _ in counts.most_common(25):
            IMPRODUTIVO_KEYWORDS.add(token)


extend_keywords_from_training()


def heuristic_classification(text: str) -> str:
    lowered = text.lower()
    for keyword in PRODUTIVO_KEYWORDS:
        if keyword in lowered:
            return "Produtivo"
    for keyword in IMPRODUTIVO_KEYWORDS:
        if keyword in lowered:
            return "Improdutivo"
    return "Produtivo"


def call_hf_classification(text: str) -> Optional[Tuple[str, float]]:
    if not HF_API_TOKEN:
        return None
    url = f"https://api-inference.huggingface.co/models/{HF_CLASSIFICATION_MODEL}"
    headers = {"Authorization": f"Bearer {HF_API_TOKEN}"}
    payload = {
        "inputs": text,
        "parameters": {
            "candidate_labels": ["Produtivo", "Improdutivo"],
            "multi_label": False,
        },
    }
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=20)
        if response.status_code != 200:
            return None
        data = response.json()
        labels = data.get("labels") or []
        scores = data.get("scores") or []
        if not labels or not scores:
            return None
        return labels[0], float(scores[0])
    except Exception:
        return None


def call_hf_generation(category: str, text: str) -> Optional[str]:
    if not HF_API_TOKEN:
        return None
    shortened = text.strip().replace("\r", " ").replace("\n", " ")
    if len(shortened) > 400:
        shortened = shortened[:400]
    if category == "Produtivo":
        tipo = "solicitação que exige ação da equipe"
    else:
        tipo = "mensagem de cortesia sem necessidade de ação imediata"
    prompt = (
        "Você é um assistente de atendimento ao cliente de uma empresa financeira. "
        "Escreva uma resposta breve, educada e profissional em português para o email a seguir, "
        f"que é uma {tipo}. "
        "Não inclua o texto original do email, apenas a resposta.\n\n"
        f"Email: {shortened}\n\nResposta:"
    )
    url = f"https://api-inference.huggingface.co/models/{HF_GENERATION_MODEL}"
    headers = {"Authorization": f"Bearer {HF_API_TOKEN}"}
    payload = {
        "inputs": prompt,
        "parameters": {
            "max_new_tokens": 120,
            "temperature": 0.7,
            "top_p": 0.9,
            "do_sample": True,
        },
    }
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        if response.status_code != 200:
            return None
        data = response.json()
        if isinstance(data, list) and data:
            generated = data[0].get("generated_text") or ""
        elif isinstance(data, dict):
            generated = data.get("generated_text") or ""
        else:
            generated = ""
        if "Resposta:" in generated:
            generated = generated.split("Resposta:", 1)[1]
        generated = generated.strip()
        if not generated:
            return None
        return generated
    except Exception:
        return None


def classify_email(text: str) -> Tuple[str, float, str]:
    processed = preprocess_text(text)
    label = None
    score = 0.0
    source = "heuristic"
    ai_result = call_hf_classification(processed or text)
    if ai_result is not None:
        label, score = ai_result
        source = "huggingface-api"
    else:
        label = heuristic_classification(text)
        score = 0.5
        source = "heuristic"
    return label, score, source


def generate_response(category: str, text: str) -> Tuple[str, str]:
    ai_reply = call_hf_generation(category, text)
    if ai_reply:
        return ai_reply, "huggingface-api"
    if category == "Produtivo":
        reply = (
            "Olá, tudo bem? Recebemos sua mensagem e já encaminhamos sua solicitação "
            "para a equipe responsável. Em breve retornaremos com uma atualização "
            "sobre o seu caso. Agradecemos o contato."
        )
    else:
        reply = (
            "Olá, muito obrigado pela sua mensagem. Agradecemos a atenção e "
            "ficamos à disposição caso precise de qualquer suporte adicional."
        )
    return reply, "template"


def extract_text_from_txt(file_storage) -> str:
    data = file_storage.read()
    try:
        return data.decode("utf-8")
    except Exception:
        return data.decode("latin-1", errors="ignore")


def extract_text_from_pdf(file_storage) -> str:
    stream = io.BytesIO(file_storage.read())
    reader = PdfReader(stream)
    pages_text = []
    for page in reader.pages:
        content = page.extract_text() or ""
        pages_text.append(content)
    return "\n".join(pages_text)


def extract_email_text(file_storage) -> str:
    filename = secure_filename(file_storage.filename or "")
    lowered = filename.lower()
    if lowered.endswith(".txt"):
        return extract_text_from_txt(file_storage)
    if lowered.endswith(".pdf"):
        return extract_text_from_pdf(file_storage)
    raise ValueError("Formato de arquivo não suportado")


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
def analyze():
    if request.is_json:
        payload = request.get_json(silent=True) or {}
        raw_text = (payload.get("email_text") or "").strip()
        file_storage = None
    else:
        raw_text = (request.form.get("email_text") or "").strip()
        file_storage = request.files.get("email_file")
    content = ""
    if file_storage and file_storage.filename:
        try:
            content = extract_email_text(file_storage)
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
    if not content:
        content = raw_text
    if not content:
        return jsonify({"error": "Nenhum conteúdo de email foi enviado."}), 400
    category, confidence, source = classify_email(content)
    reply, reply_source = generate_response(category, content)
    return jsonify(
        {
            "category": category,
            "confidence": confidence,
            "classification_source": source,
            "response": reply,
            "response_source": reply_source,
        }
    )


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=True)

