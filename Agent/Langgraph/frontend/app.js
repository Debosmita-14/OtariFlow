/* ═══════════════════════════════════════════════════════
   OtariFlow — Chat Interface (app.js)
   ═══════════════════════════════════════════════════════ */

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------
const APP = {
  sessionId: null,
  agentMode: null,
  budget: null,
  modes: [],
  sending: false,
  voiceEnabled: true,
  recording: false,
};

const $ = (id) => document.getElementById(id);

// ---------------------------------------------------------------------------
// Formatting helpers
// ---------------------------------------------------------------------------
function fmtMoney(value) {
  const amount = Number(value || 0);
  const digits = amount > 0 && amount < 0.001 ? 6 : 5;
  return `$${amount.toFixed(digits)}`;
}

function fmtPct(value) {
  return `${Math.round(Number(value || 0) * 100)}%`;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function generateId() {
  return `s_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
}

// ---------------------------------------------------------------------------
// API helper
// ---------------------------------------------------------------------------
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

// ---------------------------------------------------------------------------
// Status pill
// ---------------------------------------------------------------------------
function setStatus(kind, text) {
  const pill = $("status-pill");
  if (!pill) return;
  pill.className = `status-pill ${kind}`;
  pill.textContent = text;
}

// ---------------------------------------------------------------------------
// Budget
// ---------------------------------------------------------------------------
async function refreshBudget() {
  try {
    const budget = await api("/api/budget");
    APP.budget = budget;
    const el = $("budget-value");
    if (el) el.textContent = fmtMoney(budget.remaining);
    const meta = $("budget-meta");
    if (meta) meta.textContent = `${fmtMoney(budget.spent)} spent of ${fmtMoney(budget.total)}`;
    const fill = $("budget-fill");
    if (fill) fill.style.width = `${Math.min(100, (budget.spent / Math.max(budget.total, 0.0001)) * 100)}%`;
  } catch (e) {
    console.error("Budget refresh failed:", e);
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

// ---------------------------------------------------------------------------
// Sessions sidebar
// ---------------------------------------------------------------------------
async function refreshSessions() {
  try {
    const sessions = await api("/api/sessions");
    const list = $("session-list");
    if (!list) return;

    if (!sessions.length) {
      list.innerHTML = '<div class="muted">No chats yet.</div>';
      return;
    }

    list.innerHTML = sessions
      .map(
        (s) => `
      <div class="session-item ${s.session_id === APP.sessionId ? "active" : ""}"
           data-session-id="${escapeHtml(s.session_id)}"
           data-agent-mode="${escapeHtml(s.agent_mode || "general")}">
        <div class="session-item-title">${escapeHtml(s.title)}</div>
        <div class="session-item-meta">
          <span>${s.message_count} msg${s.message_count !== 1 ? "s" : ""}</span>
          <span>${escapeHtml(s.agent_mode || "general")}</span>
        </div>
      </div>
    `
      )
      .join("");

    list.querySelectorAll(".session-item").forEach((el) => {
      el.addEventListener("click", () => {
        const sid = el.dataset.sessionId;
        const mode = el.dataset.agentMode || "general";
        switchToSession(sid, mode);
      });
    });
  } catch (e) {
    console.error("Sessions refresh failed:", e);
  }
}

function switchToSession(sessionId, agentMode) {
  APP.sessionId = sessionId;
  APP.agentMode = agentMode;
  showChatView();
  loadSessionHistory(sessionId);
  refreshSessions();
}

// ---------------------------------------------------------------------------
// Mode picker
// ---------------------------------------------------------------------------
async function loadModes() {
  try {
    APP.modes = await api("/api/modes");
  } catch (e) {
    // Fallback modes if API fails
    APP.modes = [
      { key: "general", label: "General Chat", icon: "💬", description: "Versatile assistant for any topic." },
      { key: "coding", label: "Coding", icon: "💻", description: "Expert software engineer." },
      { key: "research", label: "Research", icon: "🔬", description: "Deep analysis assistant." },
      { key: "planner", label: "Planner Agent", icon: "📋", description: "Strategic planning." },
      { key: "task_creation", label: "Task Creation", icon: "✅", description: "Project management." },
      { key: "healthcare", label: "Healthcare Assistant", icon: "🏥", description: "Medical information." },
    ];
  }
  renderModeCards();
}

function renderModeCards() {
  const container = $("mode-cards");
  if (!container) return;
  container.innerHTML = APP.modes
    .map(
      (m) => `
    <div class="mode-card" data-mode="${escapeHtml(m.key)}">
      <div class="mode-card-icon">${m.icon || "💬"}</div>
      <div class="mode-card-label">${escapeHtml(m.label)}</div>
      <div class="mode-card-desc">${escapeHtml(m.description)}</div>
    </div>
  `
    )
    .join("");

  container.querySelectorAll(".mode-card").forEach((card) => {
    card.addEventListener("click", () => {
      const mode = card.dataset.mode;
      startNewChat(mode);
    });
  });
}

// ---------------------------------------------------------------------------
// Start new chat / show views
// ---------------------------------------------------------------------------
function startNewChat(mode) {
  APP.sessionId = generateId();
  APP.agentMode = mode || "general";
  showChatView();
  clearThread();
}

function showModePicker() {
  $("mode-picker").classList.remove("hidden");
  $("chat-view").classList.add("hidden");
}

function showChatView() {
  $("mode-picker").classList.add("hidden");
  $("chat-view").classList.remove("hidden");

  // Update mode pill
  const modeConfig = APP.modes.find((m) => m.key === APP.agentMode) || {
    icon: "💬",
    label: APP.agentMode,
  };
  const pillIcon = $("mode-pill-icon");
  const pillLabel = $("mode-pill-label");
  if (pillIcon) pillIcon.textContent = modeConfig.icon || "💬";
  if (pillLabel) pillLabel.textContent = modeConfig.label || APP.agentMode;

  // Focus input
  const input = $("prompt-input");
  if (input) setTimeout(() => input.focus(), 100);
}

function clearThread() {
  const thread = $("chat-thread");
  if (thread) thread.innerHTML = "";
}

// ---------------------------------------------------------------------------
// Load session history
// ---------------------------------------------------------------------------
async function loadSessionHistory(sessionId) {
  clearThread();
  try {
    const history = await api(`/api/session/history?session_id=${encodeURIComponent(sessionId)}`);
    for (const req of history) {
      // Add user message
      appendUserMessage(req.prompt);
      // Add assistant message with metadata
      if (req.blocked) {
        appendBlockedMessage(req);
      } else if (req.response) {
        appendAssistantMessage(req);
      }
    }
    scrollToBottom();
  } catch (e) {
    console.error("Failed to load session history:", e);
  }
}

// ---------------------------------------------------------------------------
// Message rendering
// ---------------------------------------------------------------------------
function appendUserMessage(text) {
  const thread = $("chat-thread");
  const msg = document.createElement("div");
  msg.className = "msg msg-user";
  msg.innerHTML = `
    <div class="msg-avatar">U</div>
    <div class="msg-bubble">${escapeHtml(text).replace(/\n/g, "<br>")}</div>
  `;
  thread.appendChild(msg);
}

function appendAssistantMessage(result) {
  const thread = $("chat-thread");
  const msg = document.createElement("div");
  msg.className = "msg msg-assistant";

  // Build escalation banner if applicable
  let escalationHtml = "";
  const escalations = result.escalation_history || [];
  if (escalations.length > 0) {
    const last = escalations[escalations.length - 1];
    escalationHtml = `
      <div class="escalation-banner">
        ⚡ Latency was high — upgraded from <strong>${escapeHtml(last.from_model)}</strong>
        to <strong>${escapeHtml(last.to_model)}</strong>
        (est. cost ${fmtMoney(last.estimated_cost)})
      </div>
    `;
  }

  // Format response content (basic markdown-ish rendering)
  const formatted = formatResponse(result.response || "No response generated.");

  // Build metadata section
  const metaId = `meta-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`;
  const metaHtml = buildMetaHtml(result, metaId);

  msg.innerHTML = `
    <div class="msg-avatar">⚡</div>
    <div class="msg-bubble">
      ${escalationHtml}
      <div class="msg-content">${formatted}</div>
      <div class="msg-meta-toggle" data-target="${metaId}">
        <span class="msg-meta-toggle-arrow">▼</span> Routing details
      </div>
      <div class="msg-meta" id="${metaId}">
        ${metaHtml}
      </div>
    </div>
  `;

  thread.appendChild(msg);

  // Attach toggle listener
  const toggle = msg.querySelector(".msg-meta-toggle");
  if (toggle) {
    toggle.addEventListener("click", () => {
      const target = document.getElementById(toggle.dataset.target);
      if (target) {
        target.classList.toggle("open");
        toggle.classList.toggle("open");
      }
    });
  }
}

function appendBlockedMessage(result) {
  const thread = $("chat-thread");
  const msg = document.createElement("div");
  msg.className = "msg msg-assistant";

  const metaId = `meta-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`;
  const metaHtml = buildMetaHtml(result, metaId);

  msg.innerHTML = `
    <div class="msg-avatar">🛡️</div>
    <div class="msg-bubble">
      <div class="msg-blocked">
        🚫 <strong>Blocked:</strong> ${escapeHtml(result.security_reason || "Blocked by safety or budget checks.")}
      </div>
      <div class="msg-meta-toggle" data-target="${metaId}">
        <span class="msg-meta-toggle-arrow">▼</span> Details
      </div>
      <div class="msg-meta" id="${metaId}">
        ${metaHtml}
      </div>
    </div>
  `;

  thread.appendChild(msg);

  const toggle = msg.querySelector(".msg-meta-toggle");
  if (toggle) {
    toggle.addEventListener("click", () => {
      const target = document.getElementById(toggle.dataset.target);
      if (target) {
        target.classList.toggle("open");
        toggle.classList.toggle("open");
      }
    });
  }
}

function appendErrorMessage(errorText) {
  const thread = $("chat-thread");
  const msg = document.createElement("div");
  msg.className = "msg msg-assistant";
  msg.innerHTML = `
    <div class="msg-avatar">⚠️</div>
    <div class="msg-bubble">
      <div class="msg-error">⚠️ ${escapeHtml(errorText)}</div>
    </div>
  `;
  thread.appendChild(msg);
}

function showThinking() {
  const thread = $("chat-thread");
  const el = document.createElement("div");
  el.className = "thinking-indicator";
  el.id = "thinking";
  el.innerHTML = `
    <div class="msg-avatar" style="background: linear-gradient(135deg, var(--accent), #06b6d4); color: #0a1929;">⚡</div>
    <div class="thinking-dots">
      <div class="thinking-dot"></div>
      <div class="thinking-dot"></div>
      <div class="thinking-dot"></div>
    </div>
  `;
  thread.appendChild(el);
  scrollToBottom();
}

function hideThinking() {
  const el = $("thinking");
  if (el) el.remove();
}

function scrollToBottom() {
  const thread = $("chat-thread");
  if (thread) {
    setTimeout(() => {
      thread.scrollTop = thread.scrollHeight;
    }, 50);
  }
}

// ---------------------------------------------------------------------------
// Format response text (simple markdown)
// ---------------------------------------------------------------------------
function formatResponse(text) {
  if (!text) return "";
  let html = escapeHtml(text);

  // Code blocks (```)
  html = html.replace(/```(\w*)\n([\s\S]*?)```/g, (_, lang, code) => {
    return `<pre><code>${code}</code></pre>`;
  });

  // Inline code
  html = html.replace(/`([^`]+)`/g, "<code>$1</code>");

  // Bold
  html = html.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");

  // Italic
  html = html.replace(/\*(.+?)\*/g, "<em>$1</em>");

  // Line breaks
  html = html.replace(/\n/g, "<br>");

  return html;
}

// ---------------------------------------------------------------------------
// Build metadata HTML (routing telemetry under each assistant message)
// ---------------------------------------------------------------------------
function buildMetaHtml(result, metaId) {
  const timeline = result.timeline || [];
  const whyNot = result.why_not || {};
  const scores = result.routing_scores || {};

  let html = '<div class="meta-grid">';
  html += metaItem("Risk Score", Number(result.risk_score || 0).toFixed(2));
  html += metaItem("Complexity", `${String(result.complexity_level || result.complexity || "low").toUpperCase()} (${Number(result.complexity_score || 0).toFixed(2)})`);
  html += metaItem("Model", escapeHtml(result.selected_model_label || result.selected_model || "-"));
  html += metaItem("Confidence", fmtPct(result.confidence || 0));
  html += metaItem("Est. Cost", fmtMoney(result.estimated_cost || 0));
  html += metaItem("Actual Cost", fmtMoney(result.actual_cost || 0));
  html += metaItem("Tokens", `${Number(result.actual_tokens || 0)} / ${Number(result.estimated_tokens || 0)} est`);
  html += metaItem("Latency", `${Math.round(result.latency_ms || 0)} ms`);
  if (result.cache_hit) {
    html += metaItem("Cache", `Hit (${fmtPct(result.cache_similarity || 0)})`);
  }
  html += "</div>";

  // Timeline
  if (timeline.length) {
    html += '<div class="meta-section-title">Decision Timeline</div>';
    html += '<div class="meta-timeline">';
    for (const item of timeline) {
      html += `<div class="meta-timeline-item">
        <span class="meta-timeline-status">${escapeHtml(item.status || "Step")}</span>
        <span class="meta-timeline-detail">${escapeHtml(item.detail || "")}</span>
      </div>`;
    }
    html += "</div>";
  }

  // Why not other models
  const whyEntries = Object.entries(whyNot);
  if (whyEntries.length) {
    html += '<div class="meta-section-title">Why not other models?</div>';
    html += '<div class="meta-why-not">';
    for (const [name, diff] of whyEntries) {
      html += `<div class="meta-why-not-item">
        <span class="meta-why-not-name">${escapeHtml(name)}</span>
        <span class="meta-why-not-detail">
          Cost ${fmtMoney(diff.cost_diff || 0)} | Latency ${Math.round(diff.latency_diff || 0)}ms | Quality ${(Number(diff.quality_diff || 0) * 100).toFixed(1)}%
        </span>
      </div>`;
    }
    html += "</div>";
  }

  // Routing scores
  const scoreEntries = Object.entries(scores);
  if (scoreEntries.length) {
    html += '<div class="meta-section-title">Model Scores</div>';
    html += '<div class="meta-why-not">';
    for (const [model, score] of scoreEntries) {
      html += `<div class="meta-why-not-item">
        <span class="meta-why-not-name">${escapeHtml(model)}</span>
        <span class="meta-why-not-detail">Score: ${Number(score).toFixed(3)}</span>
      </div>`;
    }
    html += "</div>";
  }

  // Escalation history
  const escalations = result.escalation_history || [];
  if (escalations.length) {
    html += '<div class="meta-section-title">Escalation History</div>';
    html += '<div class="meta-timeline">';
    for (const esc of escalations) {
      html += `<div class="meta-timeline-item">
        <span class="meta-timeline-status">${escapeHtml(esc.from_model)} → ${escapeHtml(esc.to_model)}</span>
        <span class="meta-timeline-detail">${escapeHtml(esc.reason || "")} (${fmtMoney(esc.estimated_cost)})</span>
      </div>`;
    }
    html += "</div>";
  }

  return html;
}

function metaItem(label, value) {
  return `<div class="meta-item"><span class="meta-label">${label}</span><span class="meta-value">${value}</span></div>`;
}

// ---------------------------------------------------------------------------
// Send prompt
// ---------------------------------------------------------------------------
async function sendPrompt() {
  const input = $("prompt-input");
  const prompt = input.value.trim();
  if (!prompt || APP.sending) return;

  APP.sending = true;
  const sendBtn = $("send-btn");
  if (sendBtn) sendBtn.disabled = true;

  // Clear input
  input.value = "";
  autoResize(input);

  // Append user message
  appendUserMessage(prompt);
  scrollToBottom();

  // Show thinking
  setStatus("neutral", "Thinking...");
  showThinking();

  try {
    const result = await api("/api/prompt", {
      method: "POST",
      body: JSON.stringify({
        prompt,
        session_id: APP.sessionId,
        agent_mode: APP.agentMode,
      }),
    });

    hideThinking();

    if (result.blocked) {
      appendBlockedMessage(result);
      setStatus("danger", "Blocked");
    } else {
      appendAssistantMessage(result);

      // Trigger automatic TTS playback if voice mode is enabled
      if (APP.voiceEnabled && result.response) {
        playTTS(result.response);
      }

      // Update budget
      if (result.budget) {
        APP.budget = result.budget;
        const el = $("budget-value");
        if (el) el.textContent = fmtMoney(result.budget.remaining);
        const meta = $("budget-meta");
        if (meta) meta.textContent = `${fmtMoney(result.budget.spent)} spent of ${fmtMoney(result.budget.total)}`;
        const fill = $("budget-fill");
        if (fill) fill.style.width = `${Math.min(100, (result.budget.spent / Math.max(result.budget.total, 0.0001)) * 100)}%`;
      }

      const pct = APP.budget ? APP.budget.spent / Math.max(APP.budget.total, 0.0001) : 0;
      if (pct >= 0.8) {
        setStatus("warn", "Budget warning");
      } else {
        setStatus("good", "Done");
      }
    }

    scrollToBottom();

    // Refresh session list
    refreshSessions();
  } catch (error) {
    hideThinking();
    appendErrorMessage(error.message || "Request failed.");
    setStatus("danger", "Error");
    scrollToBottom();
  } finally {
    APP.sending = false;
    if (sendBtn) sendBtn.disabled = false;
    input.focus();
  }
}

// ---------------------------------------------------------------------------
// Voice & Microphone Integration (Smallest.ai & WebSpeech API)
// ---------------------------------------------------------------------------
function toggleVoice() {
  APP.voiceEnabled = !APP.voiceEnabled;
  const btn = $("voice-toggle-btn");
  if (!btn) return;
  if (APP.voiceEnabled) {
    btn.className = "voice-toggle-btn active";
    btn.innerHTML = '<span id="voice-toggle-icon">🔊</span> Voice: ON';
  } else {
    btn.className = "voice-toggle-btn";
    btn.innerHTML = '<span id="voice-toggle-icon">🔇</span> Voice: OFF';
    if (window.speechSynthesis) window.speechSynthesis.cancel();
  }
}

function startMic() {
  if (APP.recording) return;
  const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRec) {
    alert("Speech recognition is not supported in this browser. Try Chrome or Edge.");
    return;
  }

  const recognition = new SpeechRec();
  recognition.lang = "en-US";
  recognition.interimResults = false;
  recognition.maxAlternatives = 1;

  const micBtn = $("mic-btn");
  const input = $("prompt-input");

  recognition.onstart = () => {
    APP.recording = true;
    if (micBtn) micBtn.classList.add("recording");
    if (input) input.placeholder = "Listening... Speak now!";
  };

  recognition.onspeechend = () => {
    recognition.stop();
  };

  recognition.onresult = (event) => {
    const transcript = event.results[0][0].transcript;
    if (input) {
      input.value = transcript;
      autoResize(input);
      // Automatically send the voice prompt
      setTimeout(() => sendPrompt(), 300);
    }
  };

  recognition.onerror = (event) => {
    console.error("Speech recognition error:", event.error);
  };

  recognition.onend = () => {
    APP.recording = false;
    if (micBtn) micBtn.classList.remove("recording");
    if (input) input.placeholder = "Type or click the mic to speak...";
  };

  recognition.start();
}

async function playTTS(text) {
  // Clean text of markdown formatting for cleaner speech
  const cleanText = text.replace(/```[\s\S]*?```/g, " [code block omitted] ")
                        .replace(/[*_~`#]/g, "")
                        .trim();
  if (!cleanText) return;

  try {
    setStatus("neutral", "Generating speech...");
    const res = await api("/api/tts", {
      method: "POST",
      body: JSON.stringify({ text: cleanText, voice_id: "diya" }),
    });

    if (res.status === "success" && res.audio_base64) {
      const audio = new Audio("data:audio/wav;base64," + res.audio_base64);
      audio.play();
      setStatus("good", "Playing Smallest.ai Voice");
    } else {
      // Fallback to crisp browser Web Speech API
      if (window.speechSynthesis) {
        window.speechSynthesis.cancel();
        const utterance = new SpeechSynthesisUtterance(cleanText);
        utterance.rate = 1.05;
        utterance.pitch = 1.0;
        utterance.onstart = () => setStatus("good", "Playing Voice (WebSpeech)");
        utterance.onend = () => setStatus("good", "Done");
        window.speechSynthesis.speak(utterance);
      }
    }
  } catch (err) {
    console.error("TTS API error:", err);
    // Fallback to browser Web Speech API
    if (window.speechSynthesis) {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(cleanText);
      window.speechSynthesis.speak(utterance);
    }
  }
}

// ---------------------------------------------------------------------------
// Auto-resize textarea
// ---------------------------------------------------------------------------
function autoResize(textarea) {
  textarea.style.height = "auto";
  textarea.style.height = Math.min(textarea.scrollHeight, 160) + "px";
}

// ---------------------------------------------------------------------------
// Init
// ---------------------------------------------------------------------------
document.addEventListener("DOMContentLoaded", async () => {
  // Load modes
  await loadModes();

  // Load budget
  await refreshBudget();

  // Load sessions
  await refreshSessions();

  // New chat button
  const newChatBtn = $("new-chat-btn");
  if (newChatBtn) {
    newChatBtn.addEventListener("click", () => {
      APP.sessionId = null;
      APP.agentMode = null;
      showModePicker();
      refreshSessions();
    });
  }

  // Reset budget
  const resetBtn = $("reset-btn");
  if (resetBtn) {
    resetBtn.addEventListener("click", resetBudget);
  }

  // Mode pill click → go back to mode picker
  const modePill = $("mode-pill");
  if (modePill) {
    modePill.addEventListener("click", () => {
      APP.sessionId = null;
      APP.agentMode = null;
      showModePicker();
      refreshSessions();
    });
  }

  // Voice Toggle button
  const voiceToggleBtn = $("voice-toggle-btn");
  if (voiceToggleBtn) {
    voiceToggleBtn.addEventListener("click", toggleVoice);
  }

  // Mic button
  const micBtn = $("mic-btn");
  if (micBtn) {
    micBtn.addEventListener("click", startMic);
  }

  // Send button
  const sendBtn = $("send-btn");
  if (sendBtn) {
    sendBtn.addEventListener("click", sendPrompt);
  }

  // Textarea events
  const promptInput = $("prompt-input");
  if (promptInput) {
    promptInput.addEventListener("keydown", (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
        e.preventDefault();
        sendPrompt();
      }
    });
    // Also send on Enter (without shift)
    promptInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey && !e.ctrlKey && !e.metaKey) {
        e.preventDefault();
        sendPrompt();
      }
    });
    promptInput.addEventListener("input", () => autoResize(promptInput));
  }

  // Show mode picker by default
  showModePicker();
  setStatus("neutral", "Ready");
});
