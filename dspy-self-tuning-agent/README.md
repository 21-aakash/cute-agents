# DSPy Self-Tuning Agent Studio
### Paradigm 5: Automated Compilation & Drift-Healing vs Prompt Brittleness

Part of the **[onion-agents](../README.md)** system paradigms collection.

---

## 💡 Overview

Most LLM systems rely on brittle, hand-crafted system prompts. When you:
1. **Switch models** (e.g., from GPT-4o to Llama-3-8B or Gemini Flash to reduce inference cost by 90%), or
2. **Face production data drift** (user slang, ambiguous edge cases, multi-intent queries),

...handcrafted prompts break catastrophically: JSON parsing crashes, negative policy rules get ignored, and accuracy plummets.

This project demonstrates **DSPy (Declarative Self-improving Python)**:
- Treating prompts not as hardcoded strings, but as **parameters to be compiled**.
- Using **Signatures** to define declarative input/output contracts.
- Using **`dspy.ChainOfThought`** to force explicit policy verification.
- Using **`dspy.teleprompt.BootstrapFewShot`** to automatically synthesize optimal demonstration traces.

---

## 🖥️ The 3-Panel Studio

| View | Model & Strategy | Accuracy | Strict Schema | Cost / 100k |
| :--- | :--- | :--- | :--- | :--- |
| **View 1: Vanilla Baseline** | Frontier Model + 45-line prompt | **100%** | **100%** | $2.50 |
| **View 2: Model & Data Shift** | Compact Model + Same prompt (The Breakdown) | **25%** ⚠️ | **25%** ❌ | $0.10 |
| **View 3: DSPy Compiled** | Compact Model + `BootstrapFewShot` Optimizer | **100%** ✅ | **100%** ✅ | **$0.10** *(15x cheaper)* |

---

## 🚀 Quickstart

### 1. Install Dependencies
```bash
pip install dspy fastapi uvicorn pydantic
```

### 2. Start the Studio Server
```bash
python server.py
```
Open your browser at **`http://localhost:8000`**.

---

## 📂 Project Structure

```
dspy-self-tuning-agent/
├── agent/
│   ├── dataset.py        # Standard + Production Drift test sets
│   ├── signatures.py     # Declarative DSPy input/output contract
│   ├── evaluator.py      # Quantitative policy & schema validation metrics
│   ├── vanilla_agent.py  # Handcrafted prompt baseline (Panels 1 & 2)
│   └── dspy_agent.py     # Compiled DSPy ChainOfThought module (Panel 3)
├── web/
│   ├── index.html        # Interactive 3-Panel comparison dashboard
│   ├── style.css         # Dark-mode styling & glowing metrics
│   └── app.js            # Real-time simulation and optimization controller
├── server.py             # FastAPI backend with benchmark & optimization endpoints
├── DSPY_FOUNDATIONS.md   # Complete theoretical guide to DSPy
├── USE_CASE_AND_ARCHITECTURE.md # Detailed breakdown of the dispute policy engine
└── README.md
```

---

## 🧠 Why This Matters for Production
Instead of playing "Prompt Whack-a-Mole" every time an edge case fails, DSPy brings **True CI/CD to Prompts**:
1. Add 10 failed production logs to the gold dataset.
2. Run `teleprompter.compile()`.
3. Auto-deploy the freshly tuned prompt without human trial-and-error.
