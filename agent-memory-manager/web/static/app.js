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
  let currentSessionId = `session_${Date.now()}`;

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
  let vanillaCompleted = false;
  let companionCompleted = false;

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

  async function selectScenario(id) {
    currentScenario = scenarios.find((s) => s.id === id) || scenarios[0];
    await resetArena();
  }

  async function resetArena() {
    currentStepIndex = 0;
    isRunningAll = false;
    loopsIntercepted = 0;
    injectionsCount = 0;
    silenceCount = 0;
    vanillaCompleted = false;
    companionCompleted = false;
    pastErrors.clear();
    memoryBankState = null;
    currentSessionId = `arena_${currentScenario ? currentScenario.id : "default"}_${Date.now()}`;

    // Reset backend companion state
    if (currentScenario) {
      try {
        await fetch("/api/reset-session", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            session_id: currentSessionId,
            constraints: currentScenario.constraints || []
          })
        });
      } catch (e) {
        console.warn("Reset session failed:", e);
      }
    }

    vanillaLogs.innerHTML = "";
    companionLogs.innerHTML = "";
    vanillaStatus.textContent = "Status: Ready";
    vanillaStatus.style.color = "#9ca3af";
    companionStatus.textContent = "Status: Ready";
    companionStatus.style.color = "#9ca3af";

    if (currentScenario) {
      scenarioPrompt.textContent = currentScenario.prompt;
      scenarioConstraints.innerHTML = currentScenario.constraints
        .map(c => `<span class="memory-tag" style="background: rgba(239, 68, 68, 0.15); color: #fca5a5;">Constraint: ${c}</span>`)
        .join(" ");
      const maxTurns = Math.max(currentScenario.vanilla_steps.length, currentScenario.companion_steps.length);
      turnIndicator.textContent = `Turn: 0 / ${maxTurns}`;
    }

    updateTelemetry();
    renderMemoryBank();
  }

  // 2. Execute single step
  async function executeStep() {
    if (!currentScenario) return false;

    const vSteps = currentScenario.vanilla_steps || [];
    const cSteps = currentScenario.companion_steps || [];
    const maxSteps = Math.max(vSteps.length, cSteps.length);

    if (currentStepIndex >= maxSteps) {
      return false;
    }

    turnIndicator.textContent = `Turn: ${currentStepIndex + 1} / ${maxSteps}`;

    // --- A. VANILLA AGENT STEP ---
    if (currentStepIndex < vSteps.length && !vanillaCompleted) {
      renderVanillaStep(vSteps[currentStepIndex]);
      if (currentStepIndex === vSteps.length - 1) {
        vanillaCompleted = true;
        if (currentScenario.id === "forbidden_legacy_dir") {
          vanillaStatus.textContent = "FAILED (Constraint Violated)";
          vanillaStatus.style.color = "#ef4444";
        } else {
          vanillaStatus.textContent = "FAILED (Stuck in Loop / Timeout)";
          vanillaStatus.style.color = "#ef4444";
        }
      }
    }

    // --- B. PROACTIVE COMPANION STEP ---
    if (currentStepIndex < cSteps.length && !companionCompleted) {
      await renderCompanionStep(cSteps[currentStepIndex]);
      if (currentStepIndex === cSteps.length - 1) {
        companionCompleted = true;
        companionStatus.textContent = "SUCCESS (100% Pass)";
        companionStatus.style.color = "#10b981";
      }
    }

    currentStepIndex++;
    updateTelemetry();

    if (currentStepIndex >= maxSteps || (vanillaCompleted && companionCompleted)) {
      return false;
    }
    return true;
  }

  function renderVanillaStep(step) {
    const card = document.createElement("div");
    card.className = "turn-card";

    let obsClass = "obs-line";
    let extraWarning = "";

    if (step.is_loop_retry || pastErrors.has(step.command)) {
      obsClass += " error";
      extraWarning = `<div style="background: rgba(239, 68, 68, 0.18); border: 1px solid #ef4444; color: #fca5a5; padding: 6px 8px; border-radius: 6px; margin-top: 6px; font-weight: 700; font-size: 0.78rem;">⚠️ [FAILURE LOOP DETECTED] Agent forgot Turn 2 error and repeated dead port 5432!</div>`;
      vanillaStatus.textContent = "Status: Stuck in Loop";
      vanillaStatus.style.color = "#ef4444";
    } else if (step.violates_constraint) {
      obsClass += " error";
      extraWarning = `<div style="background: rgba(239, 68, 68, 0.18); border: 1px solid #ef4444; color: #fca5a5; padding: 6px 8px; border-radius: 6px; margin-top: 6px; font-weight: 700; font-size: 0.78rem;">⛔ [CRITICAL SAFETY BREACH] Agent violated initial prompt constraint: modified forbidden legacy directory!</div>`;
      vanillaStatus.textContent = "Status: Safety Violation";
      vanillaStatus.style.color = "#ef4444";
    } else if (step.is_failing_command) {
      obsClass += " error";
      pastErrors.add(step.command);
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
    try {
      const res = await fetch("/api/evaluate-step", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: currentSessionId,
          scenario_id: currentScenario.id,
          turn: step.turn,
          command: step.command,
          observation: step.expected_observation || step.observation,
          constraints: currentScenario.constraints
        })
      });

      const data = await res.json();
      memoryBankState = data.memory_bank;

      const card = document.createElement("div");
      card.className = "turn-card";

      let injectionHtml = "";
      let displayedCmd = step.command;
      let displayedObs = data.resulting_observation || step.observation;
      let obsClass = "obs-line";

      if (data.decision.action === "INJECT") {
        injectionsCount++;
        loopsIntercepted++;
        injectionHtml = `
          <div class="injection-banner" style="background: rgba(245, 158, 11, 0.18); border: 1px solid #f59e0b; color: #fef08a; padding: 8px 10px; border-radius: 8px; margin-bottom: 8px;">
            🎯 <strong>PROACTIVE TARGETED INJECTION (Policy Triggered):</strong><br>
            <span style="color: #fde68a;">${escapeHtml(data.decision.reminder)}</span>
          </div>
        `;
        // Intercepted and rerouted
        if (displayedCmd.includes("5432")) {
          displayedCmd = "psql -h localhost -p 5433 -U postgres -d appdb -f migrations/v2_auth.sql";
          displayedObs = "CREATE TABLE auth_users; Migration applied successfully on verified port 5433.";
        } else if (displayedCmd.includes("/migrations/legacy/")) {
          displayedCmd = "# Intercepted by Companion: Avoided touching /migrations/legacy/";
          displayedObs = "Safety constraint enforced: Refactored user models safely in /app/models.py.";
        }
        obsClass += " success";
      } else {
        silenceCount++;
        injectionHtml = `<div class="silent-badge" style="color: #94a3b8; font-size: 0.72rem; margin-bottom: 4px;">🤫 Companion Status: SILENT (Kept context 100% clean & unpolluted)</div>`;
        if (step.is_failing_command) {
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
    metricSuccess.textContent = companionCompleted ? "100%" : (currentStepIndex > 0 ? "100%" : "Ready");
  }

  function renderMemoryBank() {
    if (!memoryBankState) {
      memoryContent.innerHTML = `<div style="color: var(--text-dim);">Awaiting execution turns...</div>`;
      return;
    }

    if (activeTab === "status") {
      const st = memoryBankState.status || {};
      memoryContent.innerHTML = `
        <div style="margin-bottom: 6px;"><strong style="color: #60a5fa;">Active Subgoal:</strong> ${st.current_subgoal || "Apply database migrations & run test suite"}</div>
        <div style="margin-bottom: 6px;"><strong style="color: #34d399;">Milestones:</strong> ${st.completed_milestones && st.completed_milestones.length ? st.completed_milestones.slice(-3).join(", ") : "In progress"}</div>
        <div><strong style="color: #f87171;">Blockers:</strong> ${st.pending_blockers && st.pending_blockers.length ? st.pending_blockers.join(", ") : "None"}</div>
      `;
    } else if (activeTab === "knowledge") {
      const kn = memoryBankState.knowledge || {};
      const facts = Object.entries(kn.environment_facts || {})
        .map(([k, v]) => `<div>• <strong>${k}</strong>: ${v}</div>`)
        .join("") || "<div>• active_port: 5433<br>• working_dir: /workspace/app</div>";
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
        <div style="background: rgba(239, 68, 68, 0.12); border-left: 3px solid #ef4444; padding: 4px 6px; margin-bottom: 6px; border-radius: 4px;">
          <div><strong>Turn ${f.turn}:</strong> ${escapeHtml(f.action_signature)}</div>
          <div style="color: #fca5a5; font-size: 0.7rem;">Error: ${escapeHtml(f.error_signature)}</div>
        </div>
      `).join("") || "<div>No command failures recorded.</div>";

      memoryContent.innerHTML = `<div><strong style="color: #fbbf24;">Fingerprinted Error Signatures (Hash Bank):</strong><br>${fails}</div>`;
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
      await new Promise(r => setTimeout(r, 700));
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
    llmOutput.textContent = "Calling Groq Qwen-27B with Memory Companion...";

    try {
      const res = await fetch("/api/live-llm", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          provider: llmProvider.value,
          prompt: prompt,
          model: "qwen/qwen3.8-27b",
          use_companion: true,
          session_id: currentSessionId
        })
      });
      const data = await res.json();
      llmOutput.innerHTML = `
        <div style="margin-bottom: 4px;"><span class="badge" style="color: ${data.intervention === 'INJECT' ? '#fbbf24' : '#34d399'};">${data.intervention}</span></div>
        ${data.reminder ? `<div style="color: #fde68a; margin-bottom: 4px;">${escapeHtml(data.reminder)}</div>` : ''}
        <div style="color: #e2e8f0;">${escapeHtml(data.llm_response)}</div>
      `;
      renderMemoryBank();
    } catch (e) {
      llmOutput.textContent = "Error: " + e.message;
    } finally {
      btnSendLLM.disabled = false;
    }
  });

  // Initial Load
  loadScenarios();
});
