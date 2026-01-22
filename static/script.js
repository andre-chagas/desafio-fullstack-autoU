const form = document.getElementById("email-form");
const fileInput = document.getElementById("email-file");
const textInput = document.getElementById("email-text");
const submitButton = document.getElementById("submit-button");
const submitLabel = document.getElementById("submit-label");
const submitSpinner = document.getElementById("submit-spinner");
const feedback = document.getElementById("form-feedback");

const categoryEl = document.getElementById("result-category");
const confidenceEl = document.getElementById("result-confidence");
const sourceEl = document.getElementById("result-source");
const responseEl = document.getElementById("result-response");
const copyButton = document.getElementById("copy-response-button");
const copyFeedback = document.getElementById("copy-feedback");

function setLoading(isLoading) {
  if (isLoading) {
    submitButton.disabled = true;
    submitSpinner.classList.add("visible");
    submitLabel.textContent = "Analisando...";
  } else {
    submitButton.disabled = false;
    submitSpinner.classList.remove("visible");
    submitLabel.textContent = "Analisar email";
  }
}

function setFeedback(message, type) {
  feedback.textContent = message || "";
  feedback.classList.remove("error", "success");
  if (type) {
    feedback.classList.add(type);
  }
}

function updateCategoryBadge(category) {
  categoryEl.classList.remove("badge-muted", "badge-productive", "badge-unproductive");
  if (category === "Produtivo") {
    categoryEl.classList.add("badge-productive");
  } else if (category === "Improdutivo") {
    categoryEl.classList.add("badge-unproductive");
  } else {
    categoryEl.classList.add("badge-muted");
  }
  categoryEl.textContent = category || "Indefinido";
}

function formatConfidence(confidence) {
  if (typeof confidence !== "number" || Number.isNaN(confidence)) {
    return "-";
  }
  const pct = (confidence * 100).toFixed(1);
  return `${pct.replace(".", ",")}%`;
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  setFeedback("", null);
  copyFeedback.textContent = "";

  const hasFile = fileInput.files && fileInput.files.length > 0;
  const textValue = textInput.value.trim();

  if (!hasFile && !textValue) {
    setFeedback("Envie um arquivo ou cole o texto do email para continuar.", "error");
    return;
  }

  const formData = new FormData();
  if (hasFile) {
    formData.append("email_file", fileInput.files[0]);
  }
  if (textValue) {
    formData.append("email_text", textValue);
  }

  setLoading(true);
  try {
    const response = await fetch("/analyze", {
      method: "POST",
      body: formData,
    });

    const payload = await response.json().catch(() => null);

    if (!response.ok) {
      const message =
        (payload && payload.error) ||
        "Não foi possível analisar o email. Tente novamente em instantes.";
      setFeedback(message, "error");
      return;
    }

    const category = payload.category || "Indefinido";
    const confidence = typeof payload.confidence === "number" ? payload.confidence : null;
    const source = payload.classification_source || "-";
    const reply = payload.response || "";

    updateCategoryBadge(category);
    confidenceEl.textContent = formatConfidence(confidence);
    sourceEl.textContent = source === "heuristic" ? "Regras heurísticas" : "API Hugging Face";
    responseEl.value = reply;

    setFeedback("Análise concluída com sucesso.", "success");
  } catch (error) {
    setFeedback(
      "Ocorreu um erro inesperado ao enviar o email para análise.",
      "error"
    );
  } finally {
    setLoading(false);
  }
});

copyButton.addEventListener("click", async () => {
  const text = responseEl.value.trim();
  copyFeedback.textContent = "";
  if (!text) {
    copyFeedback.textContent = "Não há resposta para copiar.";
    return;
  }
  try {
    await navigator.clipboard.writeText(text);
    copyFeedback.textContent = "Resposta copiada para a área de transferência.";
  } catch (error) {
    copyFeedback.textContent =
      "Não foi possível copiar automaticamente. Selecione e copie manualmente.";
  }
});

const themeToggleButton = document.getElementById("theme-toggle-button");

if (themeToggleButton) {
  const body = document.body;
  const storedTheme =
    typeof window !== "undefined" && window.localStorage
      ? localStorage.getItem("theme")
      : null;
  const initialTheme =
    storedTheme === "light" || storedTheme === "dark"
      ? storedTheme
      : body.getAttribute("data-theme") || "dark";

  function applyTheme(theme) {
    body.setAttribute("data-theme", theme);
    if (typeof window !== "undefined" && window.localStorage) {
      localStorage.setItem("theme", theme);
    }
    themeToggleButton.textContent =
      theme === "light" ? "Tema escuro" : "Tema claro";
  }

  applyTheme(initialTheme);

  themeToggleButton.addEventListener("click", () => {
    const current =
      body.getAttribute("data-theme") === "light" ? "light" : "dark";
    const next = current === "light" ? "dark" : "light";
    applyTheme(next);
  });
}
