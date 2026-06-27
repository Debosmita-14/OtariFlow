const state = {
  budget: null,
};

const $ = (id) => document.getElementById(id);

function fmtMoney(value) {
  const amount = Number(value || 0);
  const digits = amount > 0 && amount < 0.001 ? 6 : 5;
  return `$${amount.toFixed(digits)}`;
}

function fmtPct(value) {
  return `${Math.round((Number(value || 0)) * 100)}%`;
}

function setStatus(kind, text) {
  const pill = $("status-pill");
  pill.className = `status-pill ${kind}`;
  pill.textContent = text;
}

function setTimeline(items) {
  const root = $("timeline");
  root.innerHTML = "";
  (items || []).forEach((item) => {
    const row = document.createElement("div");
    row.className = "timeline-item";
    row.innerHTML = `<strong>${item.status || "Step"}</strong><small>${item.detail || ""}</small>`;
    root.appendChild(row);
  });
}

function setList(rootId, items, render) {
  const root = $(rootId);
  root.innerHTML = "";
  if (!items || !items.length) {
    root.innerHTML = '<div class="muted">No data yet.</div>';
    return;
  }
  items.forEach((item) => root.appendChild(render(item)));
}

function renderModelCard(model) {
  const el = document.createElement("div");
  el.className = "list-item";
  el.innerHTML = `
    <strong>${model.label || model.name || model.model_name}</strong>
    <small>Complexity ${Number(model.min_complexity ?? 0).toFixed(2)} - ${Number(model.max_complexity ?? 1).toFixed(2)}</small>
    <small>Quality ${fmtPct(model.quality_score || model.avg_confidence || 0)} | Latency ${Math.round(model.avg_latency_ms || 0)} ms</small>
    <small>Input ${fmtMoney(model.input_cost || 0)} / 1K | Output ${fmtMoney(model.output_cost || 0)} / 1K</small>
  `;
  return el;
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || response.statusText);
  }
  return response.json();
}

async function refreshBudget() {
  const budget = await api("/api/budget");
  state.budget = budget;

  $("budget-value").textContent = fmtMoney(budget.remaining);
  $("budget-meta").textContent = `${fmtMoney(budget.spent)} spent of ${fmtMoney(budget.total)}`;
  $("budget-fill").style.width = `${Math.min(100, (budget.spent / Math.max(budget.total, 0.0001)) * 100)}%`;
}

async function refreshHistory() {
  const history = await api("/api/history?limit=12");
  const table = $("history-table");
  if (!history.length) {
    table.innerHTML = '<div class="muted">No requests yet.</div>';
    return;
  }

  table.innerHTML = `
    <table>
      <thead>
        <tr>
          <th>Prompt</th>
          <th>Model</th>
          <th>Complexity</th>
          <th>Cost</th>
          <th>Status</th>
        </tr>
      </thead>
      <tbody>
        ${history.map((row) => `
          <tr>
            <td>${escapeHtml(row.prompt || "")}</td>
            <td>${escapeHtml(row.selected_model_label || row.selected_model || "-")}</td>
            <td>${escapeHtml(row.complexity || "-")}</td>
            <td>${fmtMoney(row.actual_cost || 0)}</td>
            <td>${row.blocked ? "Blocked" : row.cache_hit ? "Cache" : "Done"}</td>
          </tr>
        `).join("")}
      </tbody>
    </table>
  `;
}

async function refreshAttacks() {
  const attacks = await api("/api/attacks");
  setList("attacks-list", attacks, (attack) => {
    const el = document.createElement("div");
    el.className = "list-item";
    el.innerHTML = `
      <strong>Risk ${Number(attack.risk_score || 0).toFixed(2)}</strong>
      <small>${escapeHtml(attack.reason || "")}</small>
      <small>${escapeHtml((attack.matched_patterns || []).join(", ") || "No patterns")}</small>
    `;
    return el;
  });
}

async function refreshModels() {
  const models = await api("/api/models");
  setList("models-list", models, renderModelCard);
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function renderWhyNot(whyNot) {
  const root = $("why-not-box");
  root.innerHTML = "";
  const entries = Object.entries(whyNot || {});
  if (!entries.length) {
    root.innerHTML = '<div class="muted">No alternate model comparison for this request.</div>';
    return;
  }
  entries.forEach(([name, diff]) => {
    const el = document.createElement("div");
    el.className = "list-item";
    el.innerHTML = `
      <strong>Why not ${escapeHtml(name)}?</strong>
      <small>Cost ${fmtMoney(diff.cost_diff || 0)} | Latency ${Math.round(diff.latency_diff || 0)} ms | Quality ${(Number(diff.quality_diff || 0) * 100).toFixed(1)}%</small>
    `;
    root.appendChild(el);
  });
}

async function runPrompt() {
  const prompt = $("prompt-input").value.trim();
  if (!prompt) {
    setStatus("warn", "Prompt required");
    return;
  }

  setStatus("neutral", "Running");
  $("request-state").textContent = "Working";
  $("response-box").textContent = "Processing...";
  $("blocked-box").classList.add("hidden");

  try {
    const result = await api("/api/prompt", {
      method: "POST",
      body: JSON.stringify({ prompt, session_id: "default" }),
    });

    $("risk-score").textContent = Number(result.risk_score || 0).toFixed(2);
    $("risk-label").textContent = result.blocked ? "Blocked" : result.risk_score >= 0.6 ? "Suspicious" : "Safe";
    $("complexity-level").textContent = String(result.complexity_level || result.complexity || "low").toUpperCase();
    $("complexity-score").textContent = `Score ${Number(result.complexity_score || 0).toFixed(2)} • ${Array.isArray(result.complexity_tags) ? result.complexity_tags.join(", ") || "none" : "none"}`;
    $("selected-model").textContent = result.selected_model_label || result.selected_model || "-";
    $("selected-label").textContent = result.selected_model_id || result.selected_model || "Waiting";
    $("routing-confidence").textContent = `Confidence ${fmtPct(result.confidence || 0)}`;
    $("estimated-cost").textContent = fmtMoney(result.estimated_cost || 0);
    $("actual-cost").textContent = `Actual ${fmtMoney(result.actual_cost || 0)}`;
    $("tokens").textContent = `${Number(result.actual_tokens || 0)} actual / ${Number(result.estimated_tokens || 0)} est`;
    $("latency").textContent = `${Math.round(result.latency_ms || 0)} ms`;
    $("request-state").textContent = result.blocked ? "Blocked" : "Done";
    $("response-box").textContent = result.response || "No response was generated.";
    $("blocked-box").textContent = result.blocked ? (result.security_reason || "Blocked by safety or budget checks.") : "";
    $("blocked-box").classList.toggle("hidden", !result.blocked);
    setTimeline(result.timeline || []);
    renderWhyNot(result.why_not || {});

    const budget = await refreshBudget();
    const pct = state.budget ? (state.budget.spent / Math.max(state.budget.total, 0.0001)) : 0;
    if (result.blocked) {
      setStatus("danger", "Blocked");
    } else if (pct >= 0.8) {
      setStatus("warn", "Budget warning");
    } else {
      setStatus("good", "Routed");
    }

    await Promise.all([refreshHistory(), refreshAttacks()]);
  } catch (error) {
    setStatus("danger", "Error");
    $("request-state").textContent = "Error";
    $("response-box").textContent = error.message || "Request failed.";
  }
}

async function resetBudget() {
  const value = window.prompt("Set new budget", "5");
  if (!value) return;
  await api("/api/budget/reset", {
    method: "POST",
    body: JSON.stringify({ new_total: Number(value) }),
  });
  await refreshBudget();
}

document.addEventListener("DOMContentLoaded", async () => {
  $("run-btn").addEventListener("click", runPrompt);
  $("reset-btn").addEventListener("click", resetBudget);
  $("prompt-input").addEventListener("keydown", (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
      runPrompt();
    }
  });

  await Promise.all([refreshBudget(), refreshHistory(), refreshAttacks(), refreshModels()]);
  setStatus("neutral", "Ready");
});
