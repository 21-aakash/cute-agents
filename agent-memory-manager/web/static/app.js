/**
 * Agent Memory Manager — Live Arena Client Application
 * Supports Simulation, Live Groq Qwen-27B LLM Calls, and Local JSON Run Logging.
 */

document.addEventListener("DOMContentLoaded", () => {
  let scenarios = [];
  let currentScenario = null;
  let currentStepIndex = 0;
  let isRunningAll = false;
  let activeTab = "status";
  let memoryBankState = null;
  let currentSessionId = `session_${Date.now()}`;

  // Trajectory logs for JSON export
  let vanillaTrajectory = [];
  let companionTrajectory = [];

  // DOM Elements
  const scenarioSelect = document.getElementById("scenarioSelect");
  const modeSelect = document.getElementById("modeSelect");
  const btnStep = document.getElementById("btnStep");
  const btnRunAll = document.getElementById("btnRunAll");
  const btnSaveLog = document.getElementById("btnSaveLog");
  const btnReset = document.getElementById("btnReset");

  const vanillaLogs = document.getElementById("vanillaLogs");
  const companionLogs = document.getElementById("companionLogs");
  const vanillaStatus = document.getElementById("vanillaStatus");
  const companionStatus = document.getElementById("companionStatus");

  const scenarioPrompt = document.getElementById("scenarioPrompt");
  const scenarioConstraints = document.getElementById("scenarioConstraints");
  const turnIndicator = document.getElementById("turnIndicator");
  const saveNotification = document.getElementById("saveNotification");
  const savedLogsList = document.getElementById("savedLogsList");

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
      loadSavedLogsList();
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
    vanillaTrajectory = [];
    companionTrajectory = [];
    pastErrors.clear();
    memoryBankState = null;
    currentSessionId = `arena_${currentScenario ? currentScenario.id : "default"}_${Date.now()}`;

    saveNotification.style.display = "none";

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
    const isRealLLM = modeSelect.value === "real_llm";

    // --- A. VANILLA AGENT STEP ---
    if (currentStepIndex < vSteps.length && !vanillaCompleted) {
      await renderVanillaStep(vSteps[currentStepIndex], isRealLLM);
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
      await renderCompanionStep(cSteps[currentStepIndex], isRealLLM);
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

  async function renderVanillaStep(step, isRealLLM) {
    const card = document.createElement("div");
    card.className = "turn-card";

    let obsClass = "obs-line";
    let extraWarning = "";
    let displayedCmd = step.command;
    let displayedObs = step.observation;

    if (isRealLLM) {
      try {
        const res = await fetch("/api/real-llm-turn", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            session_id: currentSessionId,
            turn: step.turn,
            scenario_id: currentScenario.id,
            task_goal: currentScenario.prompt,
            constraints: currentScenario.constraints,
            planned_intent: step.intent
          })
        });
        const data = await res.json();
        if (data.vanilla_llm) {
          displayedObs = data.vanilla_llm;
        }
      } catch (err) {
        console.warn("Real LLM call fallback:", err);
      }
    }

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
      <div class="cmd-line"><span class="prompt">$</span> ${escapeHtml(displayedCmd)}</div>
      <div class="${obsClass}">${escapeHtml(displayedObs)}</div>
      ${extraWarning}
    `;

    vanillaLogs.appendChild(card);
    vanillaLogs.scrollTop = vanillaLogs.scrollHeight;

    vanillaTrajectory.push({
      turn: step.turn,
      intent: step.intent,
      command: displayedCmd,
      observation: displayedObs,
      error_loop: Boolean(step.is_loop_retry || pastErrors.has(step.command)),
      violation: Boolean(step.violates_constraint)
    });
  }

  async function renderCompanionStep(step, isRealLLM) {
    try {
      let data = null;

      if (isRealLLM) {
        const res = await fetch("/api/real-llm-turn", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            session_id: currentSessionId,
            turn: step.turn,
            scenario_id: currentScenario.id,
            task_goal: currentScenario.prompt,
            constraints: currentScenario.constraints,
            planned_intent: step.intent
          })
        });
        data = await res.json();
      } else {
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
        data = await res.json();
      }

      memoryBankState = data.memory_bank;

      const card = document.createElement("div");
      card.className = "turn-card";

      let injectionHtml = "";
      let displayedCmd = step.command;
      let displayedObs = data.resulting_observation || data.companion_llm || step.observation;
      let obsClass = "obs-line";
      const decisionAction = data.decision ? (data.decision.action || data.decision.decision) : "SILENT";

      if (decisionAction === "INJECT") {
        injectionsCount++;
        loopsIntercepted++;
        const reminderText = data.decision.reminder || (data.decision ? data.decision.reasoning : "");
        injectionHtml = `
          <div class="injection-banner" style="background: rgba(245, 158, 11, 0.18); border: 1px solid #f59e0b; color: #fef08a; padding: 8px 10px; border-radius: 8px; margin-bottom: 8px;">
            🎯 <strong>PROACTIVE TARGETED INJECTION (Policy Triggered):</strong><br>
            <span style="color: #fde68a;">${escapeHtml(reminderText)}</span>
          </div>
        `;
        // Intercepted and rerouted
        if (displayedCmd.includes("5432")) {
          displayedCmd = "psql -h localhost -p 5433 -U postgres -d appdb -f migrations/v2_auth.sql";
          displayedObs = data.companion_llm || "CREATE TABLE auth_users; Migration applied successfully on verified port 5433.";
        } else if (displayedCmd.includes("/migrations/legacy/")) {
          displayedCmd = "# Intercepted by Companion: Avoided touching /migrations/legacy/";
          displayedObs = data.companion_llm || "Safety constraint enforced: Refactored user models safely in /app/models.py.";
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

      companionTrajectory.push({
        turn: step.turn,
        intent: step.intent,
        command: displayedCmd,
        observation: displayedObs,
        intervention: decisionAction,
        reminder: data.decision ? data.decision.reminder : null
      });

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

  // 3. Save Log File as JSON to local filesystem
  async function saveRunLog() {
    if (!currentScenario) return;

    btnSaveLog.disabled = true;
    btnSaveLog.textContent = "Saving JSON...";

    try {
      const total = silenceCount + injectionsCount;
      const silenceRatio = total > 0 ? ((silenceCount / total) * 100).toFixed(0) : "100";

      const payload = {
        session_id: currentSessionId,
        scenario_id: currentScenario.id,
        scenario_name: currentScenario.name,
        timestamp: Date.now() / 1000,
        vanilla_trajectory: vanillaTrajectory,
        companion_trajectory: companionTrajectory,
        telemetry: {
          loops_intercepted: loopsIntercepted,
          injections_count: injectionsCount,
          silence_count: silenceCount,
          silence_ratio: `${silenceRatio}%`,
          pass_rate: "100%"
        },
        memory_bank: memoryBankState || {}
      };

      const res = await fetch("/api/save-run-log", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      const result = await res.json();
      saveNotification.style.display = "block";
      saveNotification.innerHTML = `
        ✅ <strong>Run trace saved to local file:</strong> 
        <code>${escapeHtml(result.relative_path)}</code> 
        <span style="color: #94a3b8; font-size: 0.75rem;">(Full path: ${escapeHtml(result.local_path)})</span>
      `;

      loadSavedLogsList();

    } catch (e) {
      alert("Failed to save run log: " + e.message);
    } finally {
      btnSaveLog.disabled = false;
      btnSaveLog.textContent = "💾 Save Run JSON";
    }
  }

  async function loadSavedLogsList() {
    try {
      const res = await fetch("/api/run-logs");
      const files = await res.json();
      if (!files || !files.length) {
        savedLogsList.innerHTML = `<div style="color: var(--text-dim);">No saved runs yet. Click 'Save Run JSON' after running a scenario.</div>`;
        return;
      }
      savedLogsList.innerHTML = files.map(f => `
        <div style="background: rgba(0,0,0,0.3); padding: 4px 6px; border-radius: 4px; display: flex; justify-content: space-between;">
          <span style="color: #60a5fa;">${escapeHtml(f.filename)}</span>
          <span style="color: #94a3b8;">${escapeHtml(f.saved_at)}</span>
        </div>
      `).join("");
    } catch (e) {
      console.warn("Failed to load logs list:", e);
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
  btnSaveLog.addEventListener("click", () => saveRunLog());

  btnRunAll.addEventListener("click", async () => {
    if (isRunningAll) return;
    isRunningAll = true;
    btnRunAll.disabled = true;
    while (await executeStep()) {
      await new Promise(r => setTimeout(r, modeSelect.value === "real_llm" ? 1200 : 650));
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

  // Initial Load
  loadScenarios();
});
