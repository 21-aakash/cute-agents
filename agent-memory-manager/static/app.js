/**
 * Real-time SSE Client for Proactive Memory Agent Arena
 */

let eventSource = null;

function startBenchmark() {
  const runBtn = document.getElementById("run-btn");
  const statusPill = document.getElementById("system-status");
  const baselineLogs = document.getElementById("baseline-logs");
  const proactiveLogs = document.getElementById("proactive-logs");
  const kpiStatus = document.getElementById("kpi-status");
  const kpiStepInfo = document.getElementById("kpi-step-info");

  // Reset UI
  baselineLogs.innerHTML = "";
  proactiveLogs.innerHTML = "";
  runBtn.disabled = true;
  statusPill.className = "status-pill running";
  statusPill.innerText = "Executing Benchmark...";
  kpiStatus.innerText = "Running";
  kpiStatus.className = "kpi-value yellow";

  if (eventSource) {
    eventSource.close();
  }

  eventSource = new EventSource("/api/stream-benchmark");

  eventSource.onmessage = (event) => {
    const data = JSON.parse(event.data);

    if (data.type === "AGENT_START") {
      if (data.agent === "baseline") {
        kpiStepInfo.innerText = "Phase 1: Executing Baseline Agent (No Memory)";
      } else {
        kpiStepInfo.innerText = "Phase 2: Executing Proactive Memory Agent";
      }
    } else if (data.type === "STEP") {
      renderStep(data);
    } else if (data.type === "BENCHMARK_COMPLETE") {
      handleComplete(data);
      eventSource.close();
    }
  };

  eventSource.onerror = (err) => {
    console.error("SSE connection closed/error:", err);
    runBtn.disabled = false;
    statusPill.className = "status-pill ready";
    statusPill.innerText = "Benchmark Completed";
    eventSource.close();
  };
}

function renderStep(data) {
  const container = document.getElementById(
    data.agent === "baseline" ? "baseline-logs" : "proactive-logs"
  );

  const card = document.createElement("div");
  card.className = "step-card";

  const isCrash = data.observation.toLowerCase().includes("crash") || data.observation.toLowerCase().includes("failed");
  const obsClass = isCrash ? "step-obs obs-crash" : "step-obs";

  let decisionBadge = "";
  if (data.agent === "proactive") {
    const badgeClass = data.decision === "SILENT" ? "badge-silent" : "badge-inject";
    decisionBadge = `<span class="badge-decision ${badgeClass}">[${data.decision}]</span>`;
  }

  let reminderHtml = "";
  if (data.reminder) {
    reminderHtml = `
      <div class="injection-banner">
        <strong>↳ Injected Proactive Reminder:</strong> ${escapeHtml(data.reminder)}
      </div>
    `;
  }

  card.innerHTML = `
    <div class="step-header">
      <span>Turn ${data.turn}</span>
      ${decisionBadge}
    </div>
    <div class="step-action">${escapeHtml(data.action)}</div>
    <div class="${obsClass}"><strong>Obs:</strong> ${escapeHtml(data.observation)}</div>
    ${reminderHtml}
  `;

  container.appendChild(card);
  container.scrollTop = container.scrollHeight;

  // Update Memory Inspector if proactive agent
  if (data.memory_bank) {
    updateMemoryInspector(data.memory_bank);
  }
}

function updateMemoryInspector(bank) {
  const statusEl = document.getElementById("mem-status-content");
  const knowledgeEl = document.getElementById("mem-knowledge-content");
  const proceduralEl = document.getElementById("mem-procedural-content");

  // 1. Status Memory
  let milestonesHtml = bank.milestones.map(m => `<span class="milestone-tag">✓ ${escapeHtml(m)}</span>`).join(" ");
  statusEl.innerHTML = `
    <div><strong>Active Subgoal:</strong> ${escapeHtml(bank.subgoal || "None")}</div>
    <div><strong>Completed:</strong> ${milestonesHtml || "None"}</div>
  `;

  // 2. Knowledge Memory
  let constraintsHtml = bank.constraints.map(c => `<div>• <em>${escapeHtml(c)}</em></div>`).join("");
  let factsHtml = Object.entries(bank.facts || {}).map(([k, v]) => `<div>• ${escapeHtml(k)}: <code>${escapeHtml(v)}</code></div>`).join("");
  knowledgeEl.innerHTML = `
    <div><strong>Safety Constraints:</strong></div>
    ${constraintsHtml || "None"}
    <div style="margin-top: 4px;"><strong>Discovered Facts:</strong></div>
    ${factsHtml || "<span class='empty-state'>None</span>"}
  `;

  // 3. Procedural Memory
  if (bank.failures && bank.failures.length > 0) {
    let failuresHtml = bank.failures.map(f => `
      <div class="failure-item">
        <strong>Turn ${f.turn} [${escapeHtml(f.action)}]:</strong> ${escapeHtml(f.error)}<br>
        <span style="color: #93c5fd;">↳ Fix: ${escapeHtml(f.countermeasure)}</span>
      </div>
    `).join("");
    proceduralEl.innerHTML = failuresHtml;
  } else {
    proceduralEl.innerHTML = `<div class="empty-state">No failure loops detected (Clean execution)</div>`;
  }
}

function handleComplete(data) {
  const runBtn = document.getElementById("run-btn");
  const statusPill = document.getElementById("system-status");
  const kpiStatus = document.getElementById("kpi-status");
  const kpiStepInfo = document.getElementById("kpi-step-info");
  const kpiSilence = document.getElementById("kpi-silence");

  runBtn.disabled = false;
  statusPill.className = "status-pill ready";
  statusPill.innerText = "Completed";

  kpiStatus.innerText = "Done";
  kpiStatus.className = "kpi-value green";
  kpiStepInfo.innerText = `Proactive Agent Succeeded | ${data.proactive.injections} Interventions`;

  if (data.proactive.silence_ratio !== undefined) {
    kpiSilence.innerText = `${(data.proactive.silence_ratio * 100).toFixed(1)}%`;
  }
}

function escapeHtml(text) {
  if (!text) return "";
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}
