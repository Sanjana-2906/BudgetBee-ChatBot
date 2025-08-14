# app.py — BudgetBee 🐝 (no auth)
# Run: streamlit run app.py

from __future__ import annotations

import os
import json
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

# --- OpenRouter (default) ---
OPENROUTER_API_KEY = _get("OPENROUTER_API_KEY")
OPENROUTER_MODEL   = _get("OPENROUTER_MODEL", "deepseek/deepseek-chat")

# ========= GLOBAL PROMPTS =========
SYS_PROMPT = (
    _get("SYS_PROMPT") or
    "You are BudgetBee, a concise India‑focused personal finance assistant. "
    "Answer the user's question directly in simple language. "
    "If you need more details, ask one short follow‑up."
)

def backend_name() -> str:
    return "OpenRouter" if OPENROUTER_API_KEY else "Demo Mode (rule‑based)"

# ========= LLM (OpenRouter) =========
def ask_llm(user_q: str) -> str:
    if not OPENROUTER_API_KEY:
        return (
            "AI is not configured (missing OPENROUTER_API_KEY). Here's a general tip set:\n"
            "• Track expenses weekly • Keep 3–6 months emergency fund • Use SIPs for long‑term goals\n"
            "• Compare old vs new tax regimes annually • Avoid high‑interest debt\n"
            "\nAdd an OpenRouter API key in your `.env` to enable AI answers."
        )
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
        return f"(AI error) {e}"

# ========= PROMPTS =========
def chat_system_prompt(persona: str) -> str:
    if persona.lower().startswith("stu"):
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
def budget_rules(income: float, expenses: dict) -> list[str]:
    inc = max(1.0, float(income))
    g = lambda k: float(expenses.get(k, 0))
    tips = []
    if g("Rent") > 0.30 * inc: tips.append("Rent >30% — consider renegotiating, sharing, or relocating.")
    if g("Transport") > 0.15 * inc: tips.append("Transport >15% — use passes/pooling or WFH where possible.")
    if g("Dining") > 0.10 * inc: tips.append("Dining >10% — set a weekly cap and meal‑prep twice a week.")
    if g("Subscriptions") > 0.05 * inc: tips.append("Subscriptions >5% — cancel duplicates or annualize for discounts.")
    if g("Taxes") > 0.15 * inc: tips.append("Taxes >15% — review regime choice and eligible deductions/exemptions.")
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
st.sidebar.markdown(f"**Backend:** {backend_name()}")

# Keep chat state
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
    st.session_state.chat_persona = persona
if st.session_state.chat_persona != persona:
    st.session_state.chat_history = []
    st.session_state.chat_persona = persona

# ========= PAGES =========
# ---------- CHAT ----------
if page == "Chat":
    st.subheader("Chat with BudgetBee")

    with st.expander("Debug"):
        st.write("Backend:", backend_name())
        st.write("OpenRouter key present:", bool(OPENROUTER_API_KEY))
        st.write("OpenRouter model:", OPENROUTER_MODEL)
        if "last_error" in st.session_state:
            st.error(st.session_state["last_error"])

    cols = st.columns(4)
    presets = [
        "How do I reduce taxes safely?",
        "Is 50/30/20 right for me?",
        "Best way to save ₹25k by December?",
        "Where am I overspending?",
    ]
    for i, qp in enumerate(presets):
        if cols[i].button(qp, use_container_width=True):
            st.session_state["chat_input_fill"] = qp

    for m in st.session_state.chat_history:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

    # IMPORTANT: no `value=` here; not supported on your Streamlit version
    user_msg = st.chat_input("Ask about savings, taxes, or investments (₹)…")

    # If user clicked a preset, use it as the message when there's no typed input
    default_prefill = st.session_state.pop("chat_input_fill", "")
    if not user_msg and default_prefill:
        user_msg = default_prefill

    if user_msg:
        st.session_state.chat_history.append({"role": "user", "content": user_msg})
        with st.chat_message("user"):
            st.markdown(user_msg)

        prompt = make_chat_prompt(persona, st.session_state.chat_history)
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                answer = ask_llm(prompt)
            st.markdown(answer)

        st.session_state.chat_history.append({"role": "assistant", "content": answer})

# ---------- BUDGET ----------
elif page == "Budget":
    st.subheader("Monthly Budget Analyzer")
    col1, col2 = st.columns(2)
    with col1:
        income = st.number_input("Monthly income (₹)", min_value=0.0, value=60000.0, step=1000.0)
        savings_goal = st.number_input("Planned savings this month (₹)", min_value=0.0, value=12000.0, step=1000.0)
    with col2:
        st.markdown("**Expenses by category (₹)**")
        DEFAULT_CATS = [
            "Rent", "Utilities", "Groceries", "Transport",
            "Dining", "Shopping", "Subscriptions", "Other",
            "Investments", "Taxes"
        ]
        default_vals = [20000, 3000, 8000, 4000, 3000, 2000, 800, 1500, 5000, 4000]
        expenses = {}
        for i, cat in enumerate(DEFAULT_CATS):
            expenses[cat] = st.number_input(
                cat, min_value=0.0, value=float(default_vals[i]),
                step=500.0, key=f"exp_{cat}"
            )

    if st.button("Analyze Budget"):
        total_exp = round(sum(expenses.values()), 2)
        surplus = round(income - total_exp - savings_goal, 2)
        savings_rate = 0 if income <= 0 else round(100 * savings_goal / income, 1)

        m1, m2, m3, m4 = st.columns(4)
        m1.markdown(f"<div class='metric'><h5>Income</h5><div>₹{income:.0f}</div></div>", unsafe_allow_html=True)
        m2.markdown(f"<div class='metric'><h5>Expenses</h5><div>₹{total_exp:.0f}</div></div>", unsafe_allow_html=True)
        m3.markdown(f"<div class='metric'><h5>Savings Rate</h5><div>{savings_rate:.1f}%</div></div>", unsafe_allow_html=True)
        runway = 0.0
        if income - total_exp > 0:
            runway = round((income * 3) / (income - total_exp), 1)
        m4.markdown(f"<div class='metric'><h5>Emergency Fund (est.)</h5><div>{runway:.1f} mo</div></div>", unsafe_allow_html=True)

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

        tips = budget_rules(income, expenses)
        pills = "".join([f"<span class='bee-pill'>{c}</span>" for c in sorted(expenses, key=expenses.get, reverse=True)[:3]])
        card("Top spend categories", pills or "–")
        card("Recommendations", "<ul style='margin:8px 0;'>" + "".join([f"<li>{t}</li>" for t in tips]) + "</ul>")
        ai = budget_ai_summarize(income, expenses, savings_goal, persona)
        card("AI Suggestions", f"<pre style='white-space:pre-wrap;margin:0;'>{ai}</pre>")

# ---------- GOALS ----------
elif page == "Goals":
    st.subheader("Savings Goal Planner")
    target = st.number_input("Target amount (₹)", min_value=0.0, value=25000.0, step=1000.0)
    today = date.today()
    month_plus_3 = max(1, min(12, today.month + 3))
    deadline = st.date_input("Deadline", value=date(today.year, month_plus_3, 1))
    current = st.number_input("Current savings toward this goal (₹)", min_value=0.0, value=0.0, step=1000.0)
    surplus_hint = st.number_input("Your typical monthly surplus (₹)", min_value=0.0, value=5000.0, step=500.0)

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
- **AI‑powered answers:** via OpenRouter (configurable).
- **Comprehensive support:** budgeting, tax planning, investment basics, and savings optimization.
- **Customizable personas:** Student or Professional for more relevant advice.
- **Privacy‑first:** no public sharing of your data; you control keys locally.
- **Helpful fallback:** if AI keys aren’t set, you still get safe, non‑AI tips.
""")
    st.markdown(f"**Current backend:** {backend_name()}")
    st.caption("© BudgetBee — Built with Streamlit • All amounts in ₹")
