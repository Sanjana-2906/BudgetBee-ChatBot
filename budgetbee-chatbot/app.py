# app.py — BudgetBee 🐝 (OpenRouter primary, IBM Granite fallback) — persona-ready
# Run: streamlit run app.py

from __future__ import annotations

import os
import json
import time
from datetime import date
from typing import List, Dict

import requests
import streamlit as st
from dotenv import load_dotenv, find_dotenv
from PIL import Image
import pandas as pd
import altair as alt

# ========= ENV LOADING =========
if os.path.exists("ibmcasing.env"):
    load_dotenv("ibmcasing.env")
elif os.path.exists(".env"):
    load_dotenv(".env")
else:
    load_dotenv(find_dotenv())

def _get(key: str, default: str = "") -> str:
    v = os.getenv(key, default)
    return (v or "").strip().strip('"').strip("'")

# ===== Backends =====
# OpenRouter (PRIMARY)
OPENROUTER_API_KEY = _get("OPENROUTER_API_KEY")
OPENROUTER_MODEL   = _get("OPENROUTER_MODEL", "deepseek/deepseek-chat")

# IBM Granite via Hugging Face (FALLBACK)
HF_API_TOKEN  = _get("HF_API_TOKEN")
# Use a model that exists on HF (edit if you prefer another):
HF_TEXT_MODEL = _get("HF_TEXT_MODEL", "ibm-granite/granite-3.1-8b-instruct")
USE_HF_GRANITE = _get("USE_HF_GRANITE", "1").lower() in ("1", "true", "yes")

# ========= GLOBAL PROMPTS =========
SYS_PROMPT = (
    _get("SYS_PROMPT") or
    "You are BudgetBee, a concise India‑focused personal finance assistant. "
    "Answer the user's question directly in simple language. "
    "If you need more details, ask one short follow‑up."
)

def backend_name() -> str:
    # Reflects what will be used on the next call
    if OPENROUTER_API_KEY:
        return f"OpenRouter · {OPENROUTER_MODEL}"
    if USE_HF_GRANITE and HF_API_TOKEN and HF_TEXT_MODEL:
        return f"Hugging Face (IBM Granite) · {HF_TEXT_MODEL}"
    return "Demo Mode (rule‑based)"

# ========= LLM CALLS =========
def _ask_llm_openrouter(user_q: str) -> str:
    if not OPENROUTER_API_KEY:
        return "(OpenRouter not configured)"
    try:
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://budgetbee.local",
            "X-Title": "BudgetBee",
        }
        data = {
            "model": OPENROUTER_MODEL,
            "messages": [
                {"role": "system", "content": SYS_PROMPT},
                {"role": "user", "content": user_q},
            ],
        }
        r = requests.post(url, headers=headers, data=json.dumps(data), timeout=60)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return f"(AI error via OpenRouter) {e}"

def _ask_llm_granite_hf(user_q: str) -> str:
    """Calls Hugging Face Inference API for IBM Granite; returns helpful messages on common errors."""
    if not (HF_API_TOKEN and HF_TEXT_MODEL and USE_HF_GRANITE):
        return "(Granite fallback not enabled or not configured)"
    url = f"https://api-inference.huggingface.co/models/{HF_TEXT_MODEL}"
    headers = {"Authorization": f"Bearer {HF_API_TOKEN}"}
    payload = {
        "inputs": user_q,
        "parameters": {
            "max_new_tokens": 400,
            "temperature": 0.5,
            "top_p": 0.9,
            "return_full_text": False
        }
    }
    for attempt in range(2):  # light retry for 429/503
        try:
            r = requests.post(url, headers=headers, json=payload, timeout=60)

            if r.status_code == 404:
                return (f"(Granite) HF model not found: '{HF_TEXT_MODEL}'. "
                        "Set HF_TEXT_MODEL to a valid repo id, e.g. "
                        "'ibm-granite/granite-3.1-8b-instruct' or 'ibm-granite/granite-3.3-8b-instruct'.")

            if r.status_code == 403:
                return ("(Granite) Access denied. On Hugging Face, open the model page with the SAME account "
                        "as your token, click 'Agree and access', then retry.")

            if r.status_code in (429, 503) and attempt == 0:
                time.sleep(2.0); continue

            r.raise_for_status()
            out = r.json()
            if isinstance(out, list) and out and "generated_text" in out[0]:
                return out[0]["generated_text"].strip()
            if isinstance(out, dict) and "generated_text" in out:
                return out["generated_text"].strip()
            if isinstance(out, dict) and "choices" in out:
                return out["choices"][0]["text"].strip()
            return str(out)
        except requests.exceptions.HTTPError as e:
            return f"(AI error via Hugging Face) {e}"
        except Exception as e:
            return f"(Network error via Hugging Face) {e}"
    return "(Transient error via Hugging Face) Please try again."

def ask_llm(user_q: str) -> str:
    # PRIMARY: OpenRouter
    if OPENROUTER_API_KEY:
        ans = _ask_llm_openrouter(user_q)
        # If OpenRouter fails hard, try Granite fallback:
        if ans.startswith("(AI error via OpenRouter)") and USE_HF_GRANITE and HF_API_TOKEN and HF_TEXT_MODEL:
            fallback = _ask_llm_granite_hf(user_q)
            return f"(OpenRouter error, used Granite fallback)\n\n{fallback}"
        return ans
    # FALLBACK: Granite (if enabled)
    if USE_HF_GRANITE and HF_API_TOKEN and HF_TEXT_MODEL:
        return _ask_llm_granite_hf(user_q)
    # FINAL fallback: static tips
    return (
        "AI is not configured (no OpenRouter or Granite). Quick tips:\n"
        "• Track expenses weekly • Keep 3–6 months emergency fund • Use SIPs for long‑term goals\n"
        "• Compare old vs new tax regimes annually • Avoid high‑interest debt\n"
    )

# ========= PERSONA CONFIGS =========
def persona_config(persona: str) -> Dict:
    p = (persona or "Professional").lower()
    if p.startswith("stu"):
        return {
            "name": "Student",
            "emoji": "🎒",
            "banner": (
                "Low‑cost focus: hostel/PG rent, public transport, meal‑prep, student discounts, "
                "beginner SIPs (₹500–₹1000), and basic deductions (80C/80D)."
            ),
            "caps": {"Rent": 0.35, "Transport": 0.12, "Dining": 0.08, "Subscriptions": 0.04, "Taxes": 0.10},
            "default_cats": [
                "Rent","Utilities","Groceries","Transport","Dining","Shopping","Subscriptions","Other","Investments","Taxes"
            ],
            "default_vals": [9000,1500,4000,1200,1500,1000,300,700,1000,0],
            "chat_presets": [
                "I’m a student — how do I save on food and commute?",
                "Best way to start a ₹1000 SIP?",
                "How much should my hostel rent be?",
                "Tips to build a small emergency fund?"
            ],
            "goal_hint": "For students, keep goals small and frequent (e.g., ₹5k–₹10k over 2–3 months)."
        }
    else:
        return {
            "name": "Professional",
            "emoji": "💼",
            "banner": (
                "Action focus: regime choice (old vs new), 80C/80D planning, emergency fund (3–6 months), "
                "automated SIPs/asset allocation, expense caps (rent ≤30%)."
            ),
            "caps": {"Rent": 0.30, "Transport": 0.15, "Dining": 0.10, "Subscriptions": 0.05, "Taxes": 0.15},
            "default_cats": [
                "Rent","Utilities","Groceries","Transport","Dining","Shopping","Subscriptions","Other","Investments","Taxes"
            ],
            "default_vals": [20000,3000,8000,4000,3000,2000,800,1500,5000,4000],
            "chat_presets": [
                "How do I reduce taxes safely?",
                "Is 50/30/20 right for me?",
                "Best way to save ₹25k by December?",
                "Where am I overspending?"
            ],
            "goal_hint": "Aim for consistent SIPs + emergency fund before aggressive goals."
        }

# ========= CHAT PROMPTS =========
def chat_system_prompt(persona: str) -> str:
    cfg = persona_config(persona)
    if cfg["name"] == "Student":
        role = ("You are BudgetBee, a friendly finance coach for a COLLEGE STUDENT in India (₹). "
                "Use simple sentences and low‑cost ideas (student discounts, shared housing, public transport, "
                "meal prep, beginner SIPs, basic tax deductions 80C).")
    else:
        role = ("You are BudgetBee, a concise finance coach for a WORKING PROFESSIONAL in India (₹). "
                "Be direct and action‑oriented: tax regime choice, 80C/80D planning, emergency fund sizing, "
                "automated SIPs/asset allocation, and expense caps. No product endorsements.")
    return (role +
            " Keep answers safe and general (not legal/tax advice). "
            "When user gives numbers, use them. Prefer 3–5 crisp bullets and a 1‑line Next step.")

def make_chat_prompt(persona: str, history: List[Dict[str, str]]) -> str:
    sysmsg = chat_system_prompt(persona)
    turns = history[-8:]
    dialogue = "\n".join(
        ("User: " + m["content"]) if m["role"] == "user" else ("Assistant: " + m["content"])
        for m in turns
    )
    return f"""{sysmsg}

Conversation:
{dialogue}

Guidelines:
- If the user greets you, greet back briefly and ask one relevant question about their goal.
- If the user asks a finance question, answer directly and concisely.
- Use bullets only when it helps clarity (don't force them).
- Ask at most one short follow‑up when information is missing.
- Keep answers within 5–8 short sentences unless the user asks for detail.
"""

# ========= BUDGET LOGIC =========
def budget_rules(income: float, expenses: dict, caps: Dict[str, float]) -> list[str]:
    inc = max(1.0, float(income))
    g = lambda k: float(expenses.get(k, 0))
    tips = []
    if g("Rent") > caps.get("Rent", 0.30) * inc:
        tips.append(f"Rent >{int(caps.get('Rent',0.30)*100)}% — consider renegotiating, sharing, or relocating.")
    if g("Transport") > caps.get("Transport", 0.15) * inc:
        tips.append("Transport high — use passes/pooling or WFH where possible.")
    if g("Dining") > caps.get("Dining", 0.10) * inc:
        tips.append("Dining high — set a weekly cap and meal‑prep twice a week.")
    if g("Subscriptions") > caps.get("Subscriptions", 0.05) * inc:
        tips.append("Subscriptions high — cancel duplicates or annualize for discounts.")
    if g("Taxes") > caps.get("Taxes", 0.15) * inc:
        tips.append("Taxes high — review regime choice and eligible deductions/exemptions.")
    if g("Shopping") > 0.10 * inc:
        tips.append("Shopping >10% — move impulse buys to a monthly wishlist before purchase.")
    if g("Groceries") > 0.15 * inc:
        tips.append("Groceries >15% — weekly list + bulk staples can cut 5–10%.")
    return tips

def budget_ai_summarize(income: float, expenses: dict, savings_goal: float, persona: str) -> str:
    total_exp = sum(expenses.values())
    surplus = round(income - total_exp - savings_goal, 2)
    savings_rate = 0 if income <= 0 else round(100 * savings_goal / income, 1)
    top = sorted(expenses.items(), key=lambda kv: kv[1], reverse=True)[:3]
    prompt = f"""{chat_system_prompt(persona)}

Monthly snapshot (₹):
- Income: {income}
- Total expenses: {total_exp}
- Planned savings: {savings_goal} ({savings_rate}% of income)
- Surplus after savings: {surplus}
- Top categories: {[k for k,_ in top]}

Give 5 tailored suggestions to improve savings next month (≤120 words), then 1 line on taxes & investments.
"""
    return ask_llm(prompt)

# ========= UI / THEME =========
st.set_page_config(page_title="BudgetBee — Personal Finance Assistant", page_icon="🐝", layout="wide")

CUSTOM_CSS = """
<style>
.stApp { background: linear-gradient(180deg,#ffffff 0%, #f7f8fc 60%, #ffffff 100%); }
h1,h2,h3,h4,h5,h6 { color:#1b1b1b }
.bee-card { background:#ffffff; border-radius:16px; padding:16px 18px;
  border:1px solid #e8eaf1; box-shadow:0 8px 24px rgba(0,0,0,0.06); color:#1b1b1b; }
.bee-pill{ display:inline-block; padding:4px 10px; border-radius:999px; font-size:12px;
  font-weight:600; margin-right:6px; background:#eef2ff; color:#3949ab; border:1px solid #e0e7ff; }
.metric{ flex:1 1 180px; min-width:180px; background:#ffffff; color:#1b1b1b;
  border:1px solid #e8eaf1; border-radius:14px; padding:12px 14px; box-shadow:0 8px 20px rgba(0,0,0,0.06); }
.metric h5{ margin:0; font-size:13px; opacity:.7 }
.metric div{ font-size:20px; font-weight:700; margin-top:4px }
.persona-banner{display:flex;gap:10px;align-items:flex-start;padding:10px 12px;border:1px dashed #c7d2fe;border-radius:12px;background:#f8fafc}
.persona-badge{font-weight:700}
a { color:#4f46e5 !important }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

def card(title: str, html_body: str):
    st.markdown(
        f"<div class='bee-card'><h4 style='margin:0 0 8px 0'>{title}</h4>{html_body}</div>",
        unsafe_allow_html=True
    )

# ========= HEADER =========
try:
    logo = Image.open("logo.png")
    lcol, tcol = st.columns([1, 6])
    with lcol:
        st.image(logo, width=90)
    with tcol:
        st.title("BudgetBee — Spend smart, save faster")
except Exception:
    st.title("🐝 BudgetBee — Personal Finance Assistant")

# ========= SIDEBAR =========
st.sidebar.title("BudgetBee")
page = st.sidebar.radio("Go to", ["Chat", "Budget", "Goals", "About"], index=0)
persona = st.sidebar.selectbox("Persona", ["Student", "Professional"], index=1)

# Persona config (used across pages)
CFG = persona_config(persona)

# Keep chat state + reset on persona change
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
    st.session_state.chat_persona = CFG["name"]
if st.session_state.chat_persona != CFG["name"]:
    st.session_state.chat_history = []
    st.session_state.chat_persona = CFG["name"]

# ========= PAGES =========
# ---------- CHAT ----------
if page == "Chat":
    st.subheader("Chat with BudgetBee")

    st.markdown(
        f"<div class='persona-banner'>"
        f"<div class='persona-badge'>{CFG['emoji']} <b>{CFG['name']} mode</b></div>"
        f"<div style='opacity:.85'>{CFG['banner']}</div></div>",
        unsafe_allow_html=True
    )

    with st.expander("Debug"):
        st.write("Next-call backend preference:", backend_name())
        st.write("OpenRouter key present:", bool(OPENROUTER_API_KEY))
        st.write("OpenRouter model:", OPENROUTER_MODEL)
        st.write("Granite enabled:", USE_HF_GRANITE)
        st.write("Granite HF model:", HF_TEXT_MODEL)
        if "last_error" in st.session_state:
            st.error(st.session_state["last_error"])

    cols = st.columns(4)
    for i, qp in enumerate(CFG["chat_presets"][:4]):
        if cols[i].button(qp, use_container_width=True):
            st.session_state["chat_input_fill"] = qp

    for m in st.session_state.chat_history:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

    user_msg = st.chat_input("Ask about savings, taxes, or investments (₹)…")
    default_prefill = st.session_state.pop("chat_input_fill", "")
    if not user_msg and default_prefill:
        user_msg = default_prefill

    if user_msg:
        st.session_state.chat_history.append({"role": "user", "content": user_msg})
        with st.chat_message("user"):
            st.markdown(user_msg)

        prompt = make_chat_prompt(CFG["name"], st.session_state.chat_history)
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                answer = ask_llm(prompt)
            st.markdown(answer)

        st.session_state.chat_history.append({"role": "assistant", "content": answer})

# ---------- BUDGET ----------
elif page == "Budget":
    st.subheader("Monthly Budget Analyzer")

    st.markdown(
        f"<div class='persona-banner'>"
        f"<div class='persona-badge'>{CFG['emoji']} <b>{CFG['name']} mode</b></div>"
        f"<div style='opacity:.85'>{CFG['banner']}</div></div>",
        unsafe_allow_html=True
    )

    col1, col2 = st.columns(2)
    with col1:
        default_income = 25000.0 if CFG["name"] == "Student" else 60000.0
        income = st.number_input("Monthly income (₹)", min_value=0.0, value=default_income, step=1000.0)
        default_saving = 3000.0 if CFG["name"] == "Student" else 12000.0
        savings_goal = st.number_input("Planned savings this month (₹)", min_value=0.0, value=default_saving, step=1000.0)
    with col2:
        st.markdown("**Expenses by category (₹)**")
        DEFAULT_CATS = CFG["default_cats"]
        default_vals = CFG["default_vals"]
        expenses = {}
        for i, cat in enumerate(DEFAULT_CATS):
            expenses[cat] = st.number_input(
                cat, min_value=0.0, value=float(default_vals[i]),
                step=500.0, key=f"exp_{CFG['name']}_{cat}"
            )

    if st.button("Analyze Budget"):
        total_exp = round(sum(expenses.values()), 2)
        surplus_after_saving = round(income - total_exp - savings_goal, 2)
        savings_rate = 0 if income <= 0 else round(100 * savings_goal / income, 1)

        m1, m2, m3, m4 = st.columns(4)
        m1.markdown(f"<div class='metric'><h5>Income</h5><div>₹{income:.0f}</div></div>", unsafe_allow_html=True)
        m2.markdown(f"<div class='metric'><h5>Expenses</h5><div>₹{total_exp:.0f}</div></div>", unsafe_allow_html=True)
        m3.markdown(f"<div class='metric'><h5>Savings Rate</h5><div>{savings_rate:.1f}%</div></div>", unsafe_allow_html=True)
        runway = 0.0
        if income - total_exp > 0:
            runway = round((income * 3) / (income - total_exp), 1)
        m4.markdown(f"<div class='metric'><h5>Emergency Fund (est.)</h5><div>{runway:.1f} mo</div></div>", unsafe_allow_html=True)

        if savings_goal > income:
            st.error("Not feasible: planned savings exceed income. Lower the savings goal.")
        if surplus_after_saving < 0:
            shortfall = abs(surplus_after_saving)
            st.error(f"Not feasible this month: shortfall of ₹{shortfall:.0f}. "
                     f"Reduce expenses, lower savings goal, or increase income.")

        df = pd.DataFrame([{"Category": k, "Amount": round(v, 2)} for k, v in expenses.items() if v > 0])
        if not df.empty:
            total_amt = float(df["Amount"].sum())
            df["Share"] = (df["Amount"] / total_amt * 100).round(2)
            base = alt.Chart(df).encode(
                theta=alt.Theta("Amount", stack=True),
                color=alt.Color("Category", legend=alt.Legend(title="Categories")),
                tooltip=["Category", "Amount", "Share"]
            )
            donut = base.mark_arc(outerRadius=120, innerRadius=70)
            st.altair_chart(donut, use_container_width=True)

        tips = budget_rules(income, expenses, CFG["caps"])
        pills = "".join([f"<span class='bee-pill'>{c}</span>" for c in sorted(expenses, key=expenses.get, reverse=True)[:3]])
        card("Top spend categories", pills or "–")
        ai = budget_ai_summarize(income, expenses, savings_goal, CFG["name"])
        card("Recommendations", "<ul style='margin:8px 0;'>" + "".join([f"<li>{t}</li>" for t in tips]) + "</ul>")
        card("AI Suggestions", f"<pre style='white-space:pre-wrap;margin:0;'>{ai}</pre>")

# ---------- GOALS ----------
elif page == "Goals":
    st.subheader("Savings Goal Planner")

    st.markdown(
        f"<div class='persona-banner'>"
        f"<div class='persona-badge'>{CFG['emoji']} <b>{CFG['name']} mode</b></div>"
        f"<div style='opacity:.85'>{CFG['goal_hint']}</div></div>",
        unsafe_allow_html=True
    )

    default_target = 15000.0 if CFG["name"] == "Student" else 25000.0
    default_surplus = 3000.0 if CFG["name"] == "Student" else 5000.0

    target = st.number_input("Target amount (₹)", min_value=0.0, value=default_target, step=1000.0)
    today = date.today()
    month_plus_3 = max(1, min(12, today.month + 3))
    deadline = st.date_input("Deadline", value=date(today.year, month_plus_3, 1))
    current = st.number_input("Current savings toward this goal (₹)", min_value=0.0, value=0.0, step=1000.0)
    surplus_hint = st.number_input("Your typical monthly surplus (₹)", min_value=0.0, value=default_surplus, step=500.0)

    if st.button("Plan Goal"):
        months_left = max(1, round((deadline - today).days / 30))
        needed_monthly = max(0.0, round((target - current) / months_left, 2))
        feasible = surplus_hint >= needed_monthly
        html = (f"Months left: <b>{months_left}</b><br>"
                f"Needed per month: <b>₹{needed_monthly:.2f}</b><br>"
                f"Feasible with current surplus? <b>{'Yes' if feasible else 'No'}</b>")
        card("Plan", html)
        if not feasible:
            st.info("Tip: Increase surplus (cut top leak categories) or extend the deadline.")

# ---------- ABOUT ----------
else:
    st.header("About BudgetBee")
    st.markdown("""
BudgetBee is an intelligent, privacy‑first personal finance assistant designed to help you make informed money decisions.
It analyzes budgets, goals, and questions related to savings, taxes, and investments, and gives tailored, India‑focused guidance.
""")
    st.markdown("""
**Key Features**
- **AI‑powered answers:** OpenRouter (primary) with IBM Granite via Hugging Face as fallback.
- **Comprehensive support:** budgeting, tax planning, investment basics, and savings optimization.
- **Customizable personas:** Student or Professional for more relevant advice.
- **Privacy‑first:** no public sharing of your data; you control keys locally.
- **Helpful fallback:** if AI keys aren’t set, you still get safe, non‑AI tips.
""")
    st.markdown(f"**Current preference:** {backend_name()}")
    st.caption("© BudgetBee — Built with Streamlit • All amounts in ₹")
