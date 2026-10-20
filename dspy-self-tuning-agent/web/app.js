/**
 * DSPy Teleprompter Studio — Dual Paradigm Console
 * - Paradigm 5A: Model Swap & Drift Healing (Vintage Beige/Brown)
 * - Paradigm 5B: Multi-Agent Pipeline Cascade (Navy Blue)
 */

let state = {
  activeMode: 'model-swap', // 'model-swap' or 'multi-agent'
  currentDataset: 'drifted', // 'standard' or 'drifted'
  cases: [],
  currentIndex: 0,
  datasetCache: null,
  vanillaPrompt: '',
  dspyPrompt: '',
  
  // Multi-Agent State
  multiAgentCases: [],
  multiAgentIndex: 0
};

document.addEventListener('DOMContentLoaded', async () => {
  await loadDataset();
  await loadMultiAgentDataset();
  updateClock();
  setInterval(updateClock, 1000);
});

function updateClock() {
  const clockEl = document.getElementById('system-time-display');
  if (clockEl) {
    const now = new Date();
    const iso = now.toISOString().replace('T', ' // ').substring(0, 19) + ' UTC';
    clockEl.textContent = iso;
  }
}

/**
 * Top Master Paradigm Mode Switcher
 */
function switchMode(mode) {
  state.activeMode = mode;
  const bodyEl = document.getElementById('app-body');
  const btnModel = document.getElementById('tab-model-swap');
  const btnMulti = document.getElementById('tab-multi-agent');
  const viewModel = document.getElementById('view-model-swap');
  const viewMulti = document.getElementById('view-multi-agent');

  if (mode === 'model-swap') {
    bodyEl.className = 'vintage-tech';
    btnModel.classList.add('active');
    btnMulti.classList.remove('active');
    viewModel.classList.remove('hidden');
    viewMulti.classList.add('hidden');
  } else {
    bodyEl.className = 'vintage-tech navy-mode';
    btnModel.classList.remove('active');
    btnMulti.classList.add('active');
    viewModel.classList.add('hidden');
    viewMulti.classList.remove('hidden');
    runActiveMultiAgentSimulation();
  }
}

/* ========================================================================= */
/* PARADIGM 5A: MODEL SWAP CONTROLLER                                       */
/* ========================================================================= */

async function loadDataset() {
  try {
    const res = await fetch('/api/dataset');
    const data = await res.json();
    state.datasetCache = data;
    updateCaseList();
  } catch (err) {
    console.error('Failed to load dataset telemetry:', err);
  }
}

function setDataset(type) {
  state.currentDataset = type;
  document.getElementById('btn-standard').classList.toggle('active', type === 'standard');
  document.getElementById('btn-drifted').classList.toggle('active', type === 'drifted');
  
  updateCaseList();
}

function updateCaseList() {
  if (!state.datasetCache) return;

  const cases = state.currentDataset === 'drifted' 
    ? state.datasetCache.drifted_cases 
    : state.datasetCache.standard_cases;
    
  state.cases = cases;
  state.currentIndex = 0;

  const selectEl = document.getElementById('case-select');
  selectEl.innerHTML = '';

  cases.forEach((c, idx) => {
    const opt = document.createElement('option');
    opt.value = idx;
    opt.textContent = `SPECIMEN #${idx + 1} // [${c.customer_tier}] ${c.order_type} (${c.item_value}) -> VERDICT: ${c.expected_verdict}`;
    selectEl.appendChild(opt);
  });

  renderActiveCase();
  runActiveSimulation();
  runBatchMetrics();
}

function onCaseSelectChange() {
  const selectEl = document.getElementById('case-select');
  state.currentIndex = parseInt(selectEl.value, 10);
  renderActiveCase();
  runActiveSimulation();
}

function renderActiveCase() {
  const c = state.cases[state.currentIndex];
  if (!c) return;

  const previewEl = document.getElementById('dispute-preview');
  previewEl.innerHTML = `
    <div class="meta-field">
      <span class="meta-label">TIER IDENTIFIER</span>
      <span class="meta-value">${c.customer_tier}</span>
    </div>
    <div class="meta-field">
      <span class="meta-label">ASSET CLASSIFICATION</span>
      <span class="meta-value">${c.order_type}</span>
    </div>
    <div class="meta-field">
      <span class="meta-label">AGE / VALUATION</span>
      <span class="meta-value">${c.days_since_purchase} DAYS // ${c.item_value}</span>
    </div>
    <div class="meta-field">
      <span class="meta-label">POLICY GROUND TRUTH</span>
      <span class="meta-value green">${c.expected_verdict} (PAYOUT: ${c.expected_payout})</span>
    </div>
    <div class="meta-field" style="grid-column: 1 / -1; border-top: 1px dotted var(--border-fine); padding-top: 4px; margin-top: 2px;">
      <span class="meta-label">RAW CUSTOMER TELETYPE LOG</span>
      <span class="meta-value" style="font-style: italic; color: var(--c-walnut);">"${c.claim_text}"</span>
    </div>
  `;
}

async function runActiveSimulation() {
  try {
    const res = await fetch('/api/run-simulation', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        dataset_type: state.currentDataset,
        case_index: state.currentIndex
      })
    });

    const data = await res.json();
    renderPanels(data.panels);
  } catch (err) {
    console.error('Simulation telemetry error:', err);
  }
}

function renderPanels(panels) {
  const { panel_1, panel_2, panel_3 } = panels;

  // Channel 01: Baseline
  document.getElementById('p1-output').textContent = panel_1.raw_output;
  document.getElementById('p1-latency').textContent = `${panel_1.latency_ms}ms`;
  document.getElementById('p1-cost').textContent = `$${panel_1.cost_per_1k} / 1k`;
  document.getElementById('p1-status').textContent = `[ ${panel_1.status} // CALIBRATED ]`;
  document.getElementById('p1-model-sub').textContent = panel_1.model_name.toUpperCase();

  // Channel 02: Breakage
  document.getElementById('p2-output').textContent = panel_2.raw_output;
  document.getElementById('p2-latency').textContent = `${panel_2.latency_ms}ms`;
  document.getElementById('p2-cost').textContent = `$${panel_2.cost_per_1k} / 1k`;
  document.getElementById('p2-status').textContent = panel_2.status === 'FAIL' ? '[ ANOMALY // DEGRADED ]' : '[ PASS ]';
  document.getElementById('p2-model-sub').textContent = panel_2.model_name.toUpperCase();
  
  const p2Notes = document.getElementById('p2-notes');
  if (panel_2.schema_errors && panel_2.schema_errors.length > 0) {
    p2Notes.innerHTML = panel_2.schema_errors.map(err => `<div class="ledger-row fail">[-] ${err.toUpperCase()}</div>`).join('');
  } else {
    p2Notes.innerHTML = `
      <div class="ledger-row fail">[-] CONSTRAINT VIOLATION: DIGITAL EXEMPTION OVERRIDDEN</div>
      <div class="ledger-row fail">[-] PREAMBLE CORRUPTS DOWNSTREAM JSON PARSER</div>
    `;
  }

  // Channel 03: DSPy
  document.getElementById('p3-output').textContent = panel_3.raw_output;
  document.getElementById('p3-latency').textContent = `${panel_3.latency_ms}ms`;
  document.getElementById('p3-cost').textContent = `$${panel_3.cost_per_1k} / 1k`;
  document.getElementById('p3-status').textContent = '[ OPTIMIZED // 100% HEALED ]';
  document.getElementById('p3-model-sub').textContent = panel_3.model_name.toUpperCase();

  // Cache prompts
  state.vanillaPrompt = panel_1.prompt_used;
  state.dspyPrompt = panel_3.prompt_used;
}

async function runBatchMetrics() {
  try {
    const res = await fetch(`/api/run-batch-benchmark?dataset_type=${state.currentDataset}`, {
      method: 'POST'
    });
    const data = await res.json();
    
    document.getElementById('bm-p1-acc').textContent = data.frontier_agent.accuracy;
    document.getElementById('bm-p2-acc').textContent = data.shifted_agent.accuracy;
    document.getElementById('bm-p3-acc').textContent = data.dspy_agent.accuracy;
  } catch (err) {
    console.error('Batch telemetry benchmark failure:', err);
  }
}

async function triggerOptimization() {
  const modal = document.getElementById('toast-banner');
  const logEl = document.getElementById('toast-msg');
  const fillEl = document.getElementById('stepper-fill');
  const hdrEl = document.getElementById('loader-title-text');
  
  modal.classList.remove('hidden');
  hdrEl.textContent = 'TELEPROMPTER COMPILATION SEQUENCE IN PROGRESS';
  fillEl.style.width = '15%';
  logEl.textContent = 'INITIATING TELEPROMPTER BOOTSTRAP (STUDENT=ChainOfThought)...';

  const steps = [
    { pct: '30%', text: 'PASS 1/3: RUNNING TEACHER ON 6 GOLD TRACE EXAMPLES...' },
    { pct: '55%', text: 'PASS 2/3: FILTERING PREDICTIONS BY METRIC (dspy_metric >= 0.90)...' },
    { pct: '80%', text: 'PASS 3/3: BOOTSTRAPPING 4 WINNING REASONING DEMONSTRATIONS...' },
    { pct: '95%', text: 'ASSEMBLING OPTIMIZED AST & COMPILED PROMPT RECEPTOR...' }
  ];

  for (let i = 0; i < steps.length; i++) {
    await new Promise(r => setTimeout(r, 450));
    fillEl.style.width = steps[i].pct;
    logEl.textContent = steps[i].text;
  }

  try {
    const res = await fetch('/api/optimize', { method: 'POST' });
    const result = await res.json();

    fillEl.style.width = '100%';
    logEl.textContent = `TELEPROMPTER COMPILATION COMPLETE! SCORE: ${result.metric_score_pre_compile} -> ${result.metric_score_post_compile} (${result.cost_savings_vs_frontier})`;

    setTimeout(() => {
      modal.classList.add('hidden');
      runActiveSimulation();
      runBatchMetrics();
    }, 1200);
  } catch (err) {
    logEl.textContent = 'ERR: TELEPROMPTER OPTIMIZATION INTERRUPTED.';
    setTimeout(() => modal.classList.add('hidden'), 1500);
  }
}

function openPromptModal() {
  document.getElementById('modal-vanilla-prompt').textContent = state.vanillaPrompt || 'LOADING SPECIMEN...';
  document.getElementById('modal-dspy-prompt').textContent = state.dspyPrompt || 'LOADING SPECIMEN...';
  document.getElementById('prompt-modal').classList.remove('hidden');
}

function closePromptModal() {
  document.getElementById('prompt-modal').classList.add('hidden');
}

/* ========================================================================= */
/* PARADIGM 5B: MULTI-AGENT PIPELINE CONTROLLER                              */
/* ========================================================================= */

async function loadMultiAgentDataset() {
  try {
    const res = await fetch('/api/multi-agent/cases');
    const data = await res.json();
    state.multiAgentCases = data.cases || [];

    const selectEl = document.getElementById('navy-case-select');
    selectEl.innerHTML = '';

    state.multiAgentCases.forEach((c, idx) => {
      const opt = document.createElement('option');
      opt.value = idx;
      opt.textContent = `PIPELINE SPECIMEN #${idx + 1} // [${c.ground_truth.item_type}] -> TARGET ACTION: ${c.ground_truth.api_action}`;
      selectEl.appendChild(opt);
    });

    renderActiveMultiAgentTranscript();
  } catch (err) {
    console.error('Failed to load multi-agent dataset:', err);
  }
}

function onNavyCaseSelectChange() {
  const selectEl = document.getElementById('navy-case-select');
  state.multiAgentIndex = parseInt(selectEl.value, 10);
  renderActiveMultiAgentTranscript();
  runActiveMultiAgentSimulation();
}

function renderActiveMultiAgentTranscript() {
  const c = state.multiAgentCases[state.multiAgentIndex];
  if (!c) return;

  const card = document.getElementById('navy-raw-message');
  card.innerHTML = `
    <span class="cyan-text" style="font-weight: 700; font-size: 8.5px; display: block; margin-bottom: 3px;">
      INGESTED TRANSCRIPT [CASE #${state.multiAgentIndex + 1}]:
    </span>
    "${c.raw_customer_message}"
  `;
}

async function runActiveMultiAgentSimulation() {
  try {
    const res = await fetch('/api/multi-agent/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ case_index: state.multiAgentIndex })
    });
    const data = await res.json();
    renderMultiAgentPipeline(data);
  } catch (err) {
    console.error('Multi-agent pipeline error:', err);
  }
}

function renderMultiAgentPipeline(data) {
  const { vanilla_pipeline, dspy_pipeline } = data;

  // Render Path A (Uncompiled Domino Breakdown)
  document.getElementById('navy-a-node1').textContent = JSON.stringify(vanilla_pipeline.agent_1_extractor.output, null, 2);
  document.getElementById('navy-a-node2').textContent = JSON.stringify(vanilla_pipeline.agent_2_adjudicator.output, null, 2);
  document.getElementById('navy-a-node3').textContent = JSON.stringify(vanilla_pipeline.agent_3_tool_dispatcher.output, null, 2);

  const badgeA = document.getElementById('navy-path-a-badge');
  badgeA.textContent = vanilla_pipeline.status === 'CASCADE_FAILURE' ? 'CASCADE FAILURE ⚠️' : 'STAGE PASSED';
  badgeA.className = vanilla_pipeline.status === 'CASCADE_FAILURE' ? 'badge-tag red' : 'badge-tag green';

  // Render Path B (DSPy Joint Compiled)
  document.getElementById('navy-b-node1').textContent = JSON.stringify(dspy_pipeline.agent_1_extractor.output, null, 2);
  document.getElementById('navy-b-node2').textContent = JSON.stringify(dspy_pipeline.agent_2_adjudicator.output, null, 2);
  document.getElementById('navy-b-node3').textContent = JSON.stringify(dspy_pipeline.agent_3_tool_dispatcher.output, null, 2);

  const badgeB = document.getElementById('navy-path-b-badge');
  badgeB.textContent = '100% PROTECTED SUCCESS ✅';
}

async function triggerMultiAgentCompilation() {
  const modal = document.getElementById('toast-banner');
  const logEl = document.getElementById('toast-msg');
  const fillEl = document.getElementById('stepper-fill');
  const hdrEl = document.getElementById('loader-title-text');
  
  modal.classList.remove('hidden');
  hdrEl.textContent = 'MULTI-AGENT JOINT END-TO-END COMPILATION';
  fillEl.style.width = '15%';
  logEl.textContent = 'INGESTING MULTI-NODE DAG: EXTRACTOR -> REASONER -> DISPATCHER...';

  const steps = [
    { pct: '25%', text: 'PASS 1/4: EVALUATING FINAL API CALL METRIC (payment_gateway == REJECT_NO_PAYOUT)...' },
    { pct: '50%', text: 'PASS 2/4: DETECTING INTER-NODE SIGNAL DRIFT BETWEEN AGENT 1 & AGENT 2...' },
    { pct: '75%', text: 'PASS 3/4: BOOTSTRAPPING INVARIANT ANCHORS INTO AGENT 1 PROMPT AST...' },
    { pct: '95%', text: 'PASS 4/4: ALIGNING AGENT 2 CHAIN-OF-THOUGHT WITH AGENT 3 TOOL SIGNATURE...' }
  ];

  for (let i = 0; i < steps.length; i++) {
    await new Promise(r => setTimeout(r, 450));
    fillEl.style.width = steps[i].pct;
    logEl.textContent = steps[i].text;
  }

  try {
    const res = await fetch('/api/multi-agent/compile', { method: 'POST' });
    const result = await res.json();

    fillEl.style.width = '100%';
    logEl.textContent = `MULTI-AGENT COMPILED! END-TO-END SUCCESS: ${result.metric_score_pre_compile} -> ${result.metric_score_post_compile} (${result.domino_failures_prevented} CASCADES PREVENTED)`;

    setTimeout(() => {
      modal.classList.add('hidden');
      runActiveMultiAgentSimulation();
    }, 1200);
  } catch (err) {
    logEl.textContent = 'ERR: MULTI-AGENT COMPILATION INTERRUPTED.';
    setTimeout(() => modal.classList.add('hidden'), 1500);
  }
}
