# Classificador Inteligente de Emails (Desafio AutoU)

Desenvolvido por **André Chagas**.  
Repositório: https://github.com/andre-chagas/desafio-fullstack-autoU

Aplicação web para classificar emails em **Produtivo** ou **Improdutivo** e sugerir uma **resposta automática** com apoio de inteligência artificial.

A solução foi pensada para o contexto de uma empresa financeira com alto volume de emails diários que deseja automatizar a triagem e reduzir trabalho manual da equipe.

---

## Arquitetura da solução

- **Frontend:** HTML, CSS e JavaScript
  - Formulário para upload de arquivos `.txt` ou `.pdf`
  - Campo para colar texto de email diretamente
  - Exibição da categoria, confiança e resposta sugerida
- **Backend:** Python + Flask
  - Leitura e extração de texto de `.txt` e `.pdf` (via `PyPDF2`)
  - Pré-processamento simples de NLP (lowercase, tokenização, remoção de stopwords)
  - Classificação em Produtivo/Improdutivo via:
    - API de IA da Hugging Face (se configurada)
    - Heurística baseada em palavras‑chave ajustada com dados de treinamento locais
  - Geração de resposta:
    - API de geração de texto da Hugging Face (se configurada)
    - Mensagens modelo, como fallback

---

## Como executar localmente

### 1. Pré-requisitos

- Python 3.10+ instalado
- `pip` configurado

### 2. Clonar o repositório

```bash
git clone https://github.com/andre-chagas/desafio-fullstack-autoU.git
cd desafio-fullstack-autoU
```

### 3. Criar ambiente virtual (opcional, mas recomendado)

```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
# ou
source .venv/bin/activate  # Linux/macOS
```

### 4. Instalar dependências

```bash
pip install -r requirements.txt
```

### 5. Executar a aplicação

```bash
python app.py
```

A aplicação ficará disponível em:

```text
http://localhost:5000
```

Abra esse endereço no navegador para acessar a interface web.

---

## Uso da API de IA (Hugging Face)

A aplicação está integrada à **Hugging Face Inference API** para:

- Classificar emails em **Produtivo** ou **Improdutivo**
- Gerar uma **resposta automática** personalizada

O uso da IA é **opcional**. Caso as variáveis de ambiente não sejam configuradas, a aplicação continua funcionando com heurísticas e respostas modelo.

### Variáveis de ambiente

Defina as variáveis abaixo no ambiente onde a aplicação for executada:

- `HF_API_TOKEN` (**obrigatória** para usar IA)
  - Token de acesso da Hugging Face
- `HF_CLASSIFICATION_MODEL` (opcional)
  - Padrão: `facebook/bart-large-mnli`
- `HF_GENERATION_MODEL` (opcional)
  - Padrão: `gpt2`

Exemplo em Windows (PowerShell):

```powershell
$env:HF_API_TOKEN="SEU_TOKEN_AQUI"
python app.py
```

Exemplo em Linux/macOS:

```bash
export HF_API_TOKEN="SEU_TOKEN_AQUI"
python app.py
```

Se a chamada à API falhar (sem token, timeout, erro de rede ou modelo indisponível), a aplicação automaticamente:

- Usa classificação heurística com palavras‑chave
- Gera uma resposta padrão adequada à categoria

---

## Como funciona a análise

1. **Entrada do usuário**
   - Upload de arquivo `.txt` ou `.pdf` contendo o email
   - Ou colagem do texto do email em um campo de texto
2. **Extração e pré-processamento**
   - TXT: leitura e decodificação automática (UTF‑8 / Latin‑1)
   - PDF: extração de texto página a página usando `PyPDF2`
   - NLP: lowercase, tokenização simples e remoção de stopwords PT/EN
3. **Classificação**
   - Tentativa de uso da Hugging Face Inference API com um modelo de classificação textual
   - Ajuste local da heurística usando exemplos rotulados em `training_data.json`
   - Caso não seja possível chamar a API, aplica uma heurística baseada em termos como:
     - Produtivo: `suporte`, `erro`, `problema`, `status`, `fatura`, `pagamento`, etc.
     - Improdutivo: `feliz natal`, `parabéns`, `obrigado`, `boas festas`, etc.
4. **Geração de resposta**
   - Se a API de geração estiver disponível, cria uma resposta personalizada em português
   - Caso contrário, usa uma resposta modelo adequada a cada categoria
5. **Saída na interface**
   - Categoria destacada visualmente (Produtivo/Improdutivo)
   - Confiança da classificação
   - Origem da decisão (API Hugging Face ou heurística)
   - Campo editável com a resposta sugerida e botão para copiar

---

## Endpoints principais

### `GET /`

Retorna a interface web principal.

### `POST /analyze`

Recebe o email para análise.

Formato aceito:

- `multipart/form-data` com:
  - `email_file`: arquivo `.txt` ou `.pdf` (opcional)
  - `email_text`: texto do email (opcional)
- ou `application/json` com:
  - `{"email_text": "conteúdo do email" }`

Resposta (exemplo):

```json
{
  "category": "Produtivo",
  "confidence": 0.92,
  "classification_source": "huggingface-api",
  "response": "Olá, recebemos sua mensagem...",
  "response_source": "huggingface-api"
}
```

---

## Critérios de avaliação do desafio e como a solução se encaixa

### 1. Funcionalidade e experiência do usuário

- Classificação em **Produtivo** e **Improdutivo** baseada em:
  - Modelo de classificação via Hugging Face (zero-shot) quando disponível
  - Heurística enriquecida com exemplos rotulados do domínio financeiro
- Resposta sugerida:
  - Geração automática via IA em português quando configurado
  - Respostas modelo adequadas a cada categoria como fallback
- Experiência do usuário:
  - Interface única, com upload de `.txt`/`.pdf` ou texto colado
  - Feedback visual de carregamento, mensagens de erro/sucesso e botão de copiar resposta

### 2. Qualidade técnica

- Código organizado em funções pequenas e reutilizáveis
- Separação clara entre backend (`app.py`), frontend (`templates/`, `static/`) e configuração (`requirements.txt`)
- Uso de boas práticas de HTTP (JSON estruturado, tratamento de erros e validação de entrada)

### 3. Uso de AI

- Integração com **Hugging Face Inference API** para:
  - Classificação textual (zero-shot) nas categorias Produtivo/Improdutivo
  - Geração de resposta automática em português
- Treinamento/ajuste local:
  - Arquivo `training_data.json` com exemplos reais simulados de emails
  - Pré-processamento dos exemplos e extração de tokens mais representativos por categoria
  - Esses tokens alimentam a heurística de palavras‑chave, aproximando um modelo Naive Bayes simples

### 4. Hospedagem na nuvem

- Aplicação preparada para rodar em serviços como Render/Railway:
  - Usa variável de ambiente `PORT`
  - Compatível com servidores WSGI como `gunicorn`
- Basta conectar o repositório e usar o comando:
  - `gunicorn app:app --bind 0.0.0.0:$PORT`

### 5. Interface Web (HTML)

- Interface funcional com:
  - Upload de arquivos e campo para texto
  - Exibição clara de categoria, confiança, origem da classificação e resposta sugerida
- Capricho visual:
  - Layout responsivo em duas colunas
  - Cores, gradientes e badges destacando Produtivo/Improdutivo
  - Foco em legibilidade e fluxo simples para o usuário de negócio

---

## Próximos passos e evoluções possíveis

- Treinar um modelo específico para o domínio financeiro, com exemplos reais de emails
- Salvar o histórico de classificações e respostas em um banco de dados
- Criar uma fila de processamento para alto volume de emails
- Integrar diretamente com uma caixa de email corporativa (IMAP/Exchange/Graph)
- Implementar controles de segurança e anonimização de dados sensíveis
