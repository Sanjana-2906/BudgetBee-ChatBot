# BudgetBee 🐝 — Personal Finance Assistant (Hackathon MVP)

**Goal:** Ship a working MVP in ~3 hours with clean UI, solid finance logic, and optional IBM AI.

## Quick Start
```bash
python -m venv .venv
. .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

## Optional: IBM Integration
1) Copy `.env.example` → `.env` and add your keys.
2) The app will auto-detect credentials and enhance answers with IBM services when available.

## Features
- Budget Analyzer: income, category-wise expenses, savings rate, emergency-fund months, red flags.
- Goals Planner: target amount + deadline → required monthly saving & feasibility.
- Chat: finance Q&A with persona (Student/Professional), rule-based by default, IBM-powered if keys present.
- One-file deploy: no separate backend required (Streamlit monolith for speed).

## Files
- `app.py` — Streamlit UI + orchestrator
- `finance_logic.py` — core finance calculations & rule-based insights
- `ibm_integration.py` — safe wrappers for Watson NLU & watsonx (optional)
- `prompts.py` — LLM prompt templates (kept tiny for MVP)

## Demo Flow (suggested)
1) Show **Chat**: “How do I save ₹25k for a laptop by December?”
2) Fill **Budget**: income + expenses → highlight flags & tips.
3) Use **Goals**: set target and show feasibility with current surplus.
4) Export the summary text (copy) for judges.