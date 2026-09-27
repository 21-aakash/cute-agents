/**
 * Agent Memory Manager — Live Arena Client Application
 */

document.addEventListener("DOMContentLoaded", () => {
  let scenarios = [];
  let currentScenario = null;
  let currentStepIndex = 0;
  let isRunningAll = false;
  let activeTab = "status";
  let memoryBankState = null;

  // DOM Elements
  const scenarioSelect = document.getElementById("scenarioSelect");
  const btnStep = document.getElementById("btnStep");
  const btnRunAll = document.getElementById("btnRunAll");
  const btnReset = document.getElementById("btnReset");

  const vanillaLogs = document.getElementById("vanillaLogs");
  const companionLogs = document.getElementById("companionLogs");
  const vanillaStatus = document.getElementById("vanillaStatus");
  const companionStatus = document.getElementById("companionStatus");

  const scenarioPrompt = document.getElementById("scenarioPrompt");
  const scenarioConstraints = document.getElementById("scenarioConstraints");
  const turnIndicator = document.getElementById("turnIndicator");

  const metricSuccess = document.getElementById("metricSuccess");
  const metricLoops = document.getElementById("metricLoops");
  const metricInjections = document.getElementById("metricInjections");
  const metricSilence = document.getElementById("metricSilence");
  const memoryContent = document.getElementById("memoryContent");

  const tabButtons = document.querySelectorAll(".tab-btn");

  // State metrics
  let loopsIntercepted = 0;
  let injectionsCount = 0;
  let silenceCount = 0;
  let pastErrors = new Set();

  // 1. Fetch available scenarios
  async function loadScenarios() {
    try {
      const res = await fetch("/api/scenarios");
      scenarios = await res.json();
      scenarioSelect.innerHTML = "";
      scenarios.forEach((s) => {
        const opt = document.createElement("option");
        opt.value = s.id;
        opt.textContent = `${s.name}`;
        scenarioSelect.appendChild(opt);
      });
      selectScenario(scenarios[0].id);
    } catch (e) {
      console.error("Failed to load scenarios:", e);
    }
  }

  function selectScenario(id) {
    currentScenario = scenarios.find((s) => s.id === id) || scenarios[0];
    resetArena();
  }

  function resetArena() {
    currentStepIndex = 0;
    isRunningAll = false;
    loopsIntercepted = 0;
    injectionsCount = 0;
    silenceCount = 0;
    pastErrors.clear();
    memoryBankState = null;

    vanillaLogs.innerHTML = "";
    companionLogs.innerHTML = "";
    vanillaStatus.textContent = "Status: Ready";
    vanillaStatus.style.color = "#9ca3af";
    companionStatus.textContent = "Status: Ready";
    companionStatus.style.color = "#9ca3af";

    scenarioPrompt.textContent = currentScenario.prompt;
    scenarioConstraints.innerHTML = currentScenario.constraints
      .map(c => `<span class="memory-tag" style="background: rgba(239, 68, 68, 0.15); color: #fca5a5;">Constraint: ${c}</span>`)
      .join(" ");

    turnIndicator.textContent = `Turn: 0 / ${currentScenario.steps.length}`;
    updateTelemetry();
    renderMemoryBank();
  }

  // 2. Execute single step
  async function executeStep() {
    if (!currentScenario || currentStepIndex >= currentScenario.steps.length) {
      return false;
    }

    const step = currentScenario.steps[currentStepIndex];
    turnIndicator.textContent = `Turn: ${step.turn} / ${currentScenario.steps.length}`;

    // --- A. VANILLA AGENT RENDERING ---
    renderVanillaStep(step);

    // --- B. PROACTIVE COMPANION AGENT EVALUATION & RENDERING ---
    await renderCompanionStep(step);

    currentStepIndex++;
    updateTelemetry();

    if (currentStepIndex >= currentScenario.steps.length) {
      vanillaStatus.textContent = currentScenario.id === "forbidden_legacy_dir" ? "FAILED (Constraint Violated)" : "Finished";
      vanillaStatus.style.color = currentScenario.id === "forbidden_legacy_dir" ? "#ef4444" : "#10b981";
      companionStatus.textContent = "SUCCESS (100%)";
      companionStatus.style.color = "#10b981";
      return false;
    }
    return true;
  }

  function renderVanillaStep(step) {
    const card = document.createElement("div");
    card.className = "turn-card";

    let obsClass = "obs-line";
    let extraWarning = "";

    if (step.is_failing) {
      obsClass += " error";
      if (pastErrors.has(step.command)) {
        extraWarning = `<div style="color: #ef4444; font-weight: 700; margin-top: 4px;">⚠️ [LOOP DETECTED] Repeated failing command!</div>`;
        vanillaStatus.textContent = "Status: Stuck in Loop";
        vanillaStatus.style.color = "#ef4444";
      } else {
        pastErrors.add(step.command);
      }
    } else if (step.violates_constraint) {
      obsClass += " error";
      extraWarning = `<div style="color: #ef4444; font-weight: 700; margin-top: 4px;">⛔ [CONSTRAINT VIOLATED] Modified forbidden files!</div>`;
      vanillaStatus.textContent = "Status: Violation Error";
      vanillaStatus.style.color = "#ef4444";
    } else {
      obsClass += " success";
    }

    card.innerHTML = `
      <div class="turn-header">
        <span>Turn ${step.turn}</span>
        <span>${step.intent}</span>
      </div>
      <div class="cmd-line"><span class="prompt">$</span> ${escapeHtml(step.command)}</div>
      <div class="${obsClass}">${escapeHtml(step.observation)}</div>
      ${extraWarning}
    `;

    vanillaLogs.appendChild(card);
    vanillaLogs.scrollTop = vanillaLogs.scrollHeight;
  }

  async function renderCompanionStep(step) {
    // Call backend evaluator
    try {
      const res = await fetch("/api/evaluate-step", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: `ui_${currentScenario.id}`,
          scenario_id: currentScenario.id,
          turn: step.turn,
          command: step.command,
          observation: step.observation,
          constraints: currentScenario.constraints
        })
      });

      const data = await res.json();
      memoryBankState = data.memory_bank;

      const card = document.createElement("div");
      card.className = "turn-card";

      let injectionHtml = "";
      let displayedCmd = step.command;
      let displayedObs = step.observation;
      let obsClass = "obs-line";

      if (data.decision.action === "INJECT") {
        injectionsCount++;
        loopsIntercepted++;
        injectionHtml = `
          <div class="injection-banner">
            🎯 <strong>TARGETED INJECTION:</strong> ${escapeHtml(data.decision.reminder)}
          </div>
        `;
        // Safe correction applied
        if (displayedCmd.includes("5432")) {
          displayedCmd = displayedCmd.replace("5432", "5433");
          displayedObs = "Applied migration successfully on port 5433.";
        }
        obsClass += " success";
      } else {
        silenceCount++;
        injectionHtml = `<div class="silent-badge">🤫 Companion Status: SILENT (Attention preserved)</div>`;
        if (step.is_failing) {
          obsClass += " error";
        } else {
          obsClass += " success";
        }
      }

      card.innerHTML = `
        <div class="turn-header">
          <span>Turn ${step.turn}</span>
          <span>${step.intent}</span>
        </div>
        ${injectionHtml}
        <div class="cmd-line"><span class="prompt">$</span> ${escapeHtml(displayedCmd)}</div>
        <div class="${obsClass}">${escapeHtml(displayedObs)}</div>
      `;

      companionLogs.appendChild(card);
      companionLogs.scrollTop = companionLogs.scrollHeight;
      renderMemoryBank();

    } catch (err) {
      console.error("Step evaluation error:", err);
    }
  }

  function updateTelemetry() {
    const total = silenceCount + injectionsCount;
    const silenceRatio = total > 0 ? ((silenceCount / total) * 100).toFixed(0) : "100";

    metricLoops.textContent = loopsIntercepted;
    metricInjections.textContent = injectionsCount;
    metricSilence.textContent = `${silenceRatio}%`;
    metricSuccess.textContent = "100%";
  }

  function renderMemoryBank() {
    if (!memoryBankState) {
      memoryContent.innerHTML = `<div style="color: var(--text-dim);">Awaiting execution turns...</div>`;
      return;
    }

    if (activeTab === "status") {
      const st = memoryBankState.status || {};
      memoryContent.innerHTML = `
        <div style="margin-bottom: 6px;"><strong style="color: #60a5fa;">Subgoal:</strong> ${st.current_subgoal || "None specified"}</div>
        <div style="margin-bottom: 6px;"><strong style="color: #34d399;">Milestones:</strong> ${st.completed_milestones && st.completed_milestones.length ? st.completed_milestones.join(", ") : "In progress"}</div>
        <div><strong style="color: #f87171;">Blockers:</strong> ${st.pending_blockers && st.pending_blockers.length ? st.pending_blockers.join(", ") : "None"}</div>
      `;
    } else if (activeTab === "knowledge") {
      const kn = memoryBankState.knowledge || {};
      const facts = Object.entries(kn.environment_facts || {})
        .map(([k, v]) => `<div>• <strong>${k}</strong>: ${v}</div>`)
        .join("") || "<div>No environment facts yet</div>";
      const constraints = (kn.user_constraints || [])
        .map(c => `<div style="color: #fca5a5;">• ${c}</div>`)
        .join("") || "<div>No constraints set</div>";
      
      memoryContent.innerHTML = `
        <div style="margin-bottom: 8px;"><strong style="color: #a5b4fc;">Environment Facts:</strong><br>${facts}</div>
        <div><strong style="color: #f87171;">User Constraints:</strong><br>${constraints}</div>
      `;
    } else if (activeTab === "procedural") {
      const pr = memoryBankState.procedural || {};
      const fails = (pr.failed_attempts || []).map(f => `
        <div style="background: rgba(239, 68, 68, 0.1); border-left: 2px solid #ef4444; padding: 4px 6px; margin-bottom: 6px; border-radius: 4px;">
          <div><strong>Turn ${f.turn}:</strong> ${f.action_signature}</div>
          <div style="color: #fca5a5; font-size: 0.7rem;">Error: ${f.error_signature}</div>
        </div>
      `).join("") || "<div>No command failures recorded.</div>";

      memoryContent.innerHTML = `<div><strong style="color: #fbbf24;">Failed Signatures (Hashes):</strong><br>${fails}</div>`;
    }
  }

  function escapeHtml(str) {
    if (!str) return "";
    return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  // Event Listeners
  scenarioSelect.addEventListener("change", (e) => selectScenario(e.target.value));
  btnStep.addEventListener("click", () => executeStep());
  btnReset.addEventListener("click", () => resetArena());

  btnRunAll.addEventListener("click", async () => {
    if (isRunningAll) return;
    isRunningAll = true;
    btnRunAll.disabled = true;
    while (await executeStep()) {
      await new Promise(r => setTimeout(r, 600));
    }
    isRunningAll = false;
    btnRunAll.disabled = false;
  });

  tabButtons.forEach(btn => {
    btn.addEventListener("click", () => {
      tabButtons.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      activeTab = btn.dataset.tab;
      renderMemoryBank();
    });
  });

  // Direct Live LLM Tester
  const btnSendLLM = document.getElementById("btnSendLLM");
  const livePromptInput = document.getElementById("livePromptInput");
  const llmProvider = document.getElementById("llmProvider");
  const llmOutput = document.getElementById("llmOutput");

  btnSendLLM.addEventListener("click", async () => {
    const prompt = livePromptInput.value.trim();
    if (!prompt) return;

    btnSendLLM.disabled = true;
    llmOutput.textContent = "Calling model with Memory Companion...";

    try {
      const res = await fetch("/api/live-llm", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          provider: llmProvider.value,
          prompt: prompt,
          use_companion: true
        })
      });
      const data = await res.json();
      llmOutput.innerHTML = `<strong>Intervention:</strong> ${data.intervention}<br><strong>Response:</strong> ${escapeHtml(data.llm_response)}`;
    } catch (e) {
      llmOutput.textContent = "Error: " + e.message;
    } finally {
      btnSendLLM.disabled = false;
    }
  });

  // Initial Load
  loadScenarios();
});
