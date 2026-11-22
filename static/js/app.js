const resultBox = document.getElementById("result");

function showPanel(panelId) {
  document.querySelectorAll(".tool-panel").forEach(panel => panel.classList.add("hidden"));
  const selected = document.getElementById(panelId);
  selected.classList.remove("hidden");
  document.getElementById("panel-title").textContent = selected.querySelector("h3").textContent;
  document.getElementById("panel-subtitle").textContent = "Enter your details and submit to receive guidance.";
  resultBox.innerHTML = '<div class="empty-state"><span>🌱</span><h3>Your result will appear here</h3><p>Submit the form to get started.</p></div>';
  document.getElementById("workspace").scrollIntoView({behavior:"smooth"});
}

function showLoading(message = "KrishiMitra is preparing your response...") {
  resultBox.innerHTML = `<p class="loading">⏳ ${escapeHtml(message)}</p>`;
}

function showResult(text) {
  resultBox.textContent = text;
  resultBox.scrollTop = 0;
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, char => ({
    "&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;", "'":"&#039;"
  }[char]));
}

async function postJson(url, payload) {
  const response = await fetch(url, {
    method:"POST",
    headers:{"Content-Type":"application/json"},
    body:JSON.stringify(payload)
  });
  const data = await response.json();
  if (!response.ok || !data.success) throw new Error(data.error || "Something went wrong.");
  return data;
}

document.getElementById("crop-form").addEventListener("submit", async event => {
  event.preventDefault();
  const payload = Object.fromEntries(new FormData(event.target).entries());
  showLoading("Finding suitable crop options...");
  try {
    const data = await postJson("/api/crop-recommendation", payload);
    showResult(data.answer);
    loadHistory();
  } catch (error) { showResult("Error: " + error.message); }
});

document.getElementById("disease-form").addEventListener("submit", async event => {
  event.preventDefault();
  const formData = new FormData(event.target);
  showLoading("Reviewing the leaf image...");
  try {
    const response = await fetch("/api/disease-detection", {method:"POST", body:formData});
    const data = await response.json();
    if (!response.ok || !data.success) throw new Error(data.error || "Image analysis failed.");
    showResult(data.answer);
    loadHistory();
  } catch (error) { showResult("Error: " + error.message); }
});

document.querySelectorAll(".advice-form").forEach(form => {
  form.addEventListener("submit", async event => {
    event.preventDefault();
    const details = new FormData(form).get("details");
    showLoading("Preparing farming guidance...");
    try {
      const data = await postJson("/api/farm-advice", {
        feature:form.dataset.feature, details
      });
      showResult(data.answer);
      loadHistory();
    } catch (error) { showResult("Error: " + error.message); }
  });
});

function addMessage(text, who) {
  const messages = document.getElementById("messages");
  const bubble = document.createElement("div");
  bubble.className = "message " + (who === "user" ? "user-message" : "bot-message");
  bubble.textContent = text;
  messages.appendChild(bubble);
  messages.scrollTop = messages.scrollHeight;
}

document.getElementById("chat-form").addEventListener("submit", async event => {
  event.preventDefault();
  const input = document.getElementById("chat-message");
  const message = input.value.trim();
  if (!message) return;
  addMessage(message, "user");
  input.value = "";
  const pending = "KrishiBot is thinking...";
  addMessage(pending, "bot");
  const messages = document.getElementById("messages");
  try {
    const data = await postJson("/api/chat", {message});
    messages.lastElementChild.textContent = data.answer;
    loadHistory();
  } catch (error) {
    messages.lastElementChild.textContent = "Sorry, " + error.message;
  }
  messages.scrollTop = messages.scrollHeight;
});

function useSuggestion(text) {
  document.getElementById("chat-message").value = text;
  document.getElementById("chat-message").focus();
}

async function loadHistory() {
  const container = document.getElementById("history-list");
  try {
    const response = await fetch("/api/history");
    const data = await response.json();
    if (!data.success || !data.reports.length) {
      container.innerHTML = '<p class="muted">No reports yet. Use a tool to create your first report.</p>';
      return;
    }
    container.innerHTML = data.reports.map(report => `
      <article class="history-item">
        <b>${escapeHtml(report.feature)}</b>
        <small>${escapeHtml(report.created_at.replace("T", " "))}</small>
        <p>${escapeHtml(report.ai_response.slice(0, 240))}${report.ai_response.length > 240 ? "…" : ""}</p>
      </article>
    `).join("");
  } catch {
    container.innerHTML = '<p class="muted">Could not load report history.</p>';
  }
}

loadHistory();
