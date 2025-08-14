from datetime import date
from typing import Dict, List, Tuple

DEFAULT_CATS = [
    "Rent", "Utilities", "Groceries", "Transport",
    "Dining", "Shopping", "Subscriptions", "Other",
    "Investments", "Taxes"   
]

def pct(part, whole):
    return 0 if whole == 0 else round(100 * part / whole, 2)

def compute_summary(income: float, expenses: Dict[str, float], savings_goal: float):
    total_expenses = round(sum(expenses.values()), 2)
    savings_rate = pct(savings_goal, income)
    expense_shares = {k: {"amount": round(v,2), "pct": pct(v, income)} for k, v in expenses.items()}
    top = sorted(expenses.items(), key=lambda x: x[1], reverse=True)[:3]
    surplus = round(income - total_expenses - savings_goal, 2)
    emergency_months = round((income * 3) / max(1, income - total_expenses), 2) if income > total_expenses else 0
    return {
        "income": income,
        "total_expenses": total_expenses,
        "savings_goal": savings_goal,
        "savings_rate": savings_rate,
        "expense_shares": expense_shares,
        "top_categories": [k for k,_ in top],
        "surplus": surplus,
        "surplus_positive": surplus >= 0,
        "emergency_fund_months": emergency_months
    }

def rules(summary: dict, persona: str) -> List[str]:
    tips = []
    inc = summary["income"]
    exp = summary["total_expenses"]
    shares = {k: v["amount"] for k, v in summary["expense_shares"].items()}
    # Benchmarks
    if shares.get("Rent", 0) > 0.3 * inc:
        tips.append("Rent >30% of income — consider renegotiating, sharing, or relocating.")
    if shares.get("Transport", 0) > 0.15 * inc:
        tips.append("Transport >15% — explore passes, pooling, or WFH days.")
    if shares.get("Dining", 0) > 0.10 * inc:
        tips.append("Dining >10% — set a weekly cap and meal-prep twice a week.")
    if shares.get("Subscriptions", 0) > 0.05 * inc:
        tips.append("Subscriptions >5% — cancel duplicates or annualize for discounts.")
    if summary["savings_rate"] < 20:
        tips.append("Increase savings rate toward 20% (50/30/20 rule). Automate transfers on payday.")
    if shares.get("Taxes", 0) > 0.15 * inc:
        tips.append("Taxes >15% — review declarations, eligible deductions/exemptions, and confirm you’re on the right tax regime.")
    if not summary["surplus_positive"]:
        tips.append("Negative surplus — pause wants for a month and sell one unused item to plug the gap.")
    # Persona flavor
    pl = (persona or '').lower()
    if pl.startswith('stu'):
        tips.append("Student tip: use student IDs for transit/OTT discounts and library resources.")
    elif pl.startswith('pro'):
        tips.append("Pro tip: set up salary auto-sweep into liquid fund for idle cash.")
    return tips[:6]

def goal_plan(target_amount: float, deadline: date, current_savings: float, monthly_surplus: float) -> Dict:
    days_left = (deadline - date.today()).days
    months_left = max(1, round(days_left / 30))
    needed_monthly = max(0.0, round((target_amount - current_savings) / months_left, 2))
    feasible = monthly_surplus >= needed_monthly
    return {
        "months_left": months_left,
        "needed_monthly": needed_monthly,
        "feasible": feasible
    }