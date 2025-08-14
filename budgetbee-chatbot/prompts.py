STUDENT_TONE = "Explain like I'm a college student. Be friendly, concrete, and action-focused."
PRO_TONE = "Explain like I'm a busy young professional. Be concise, data-driven, and specific."

def make_budget_prompt(summary, persona: str):
    tone = STUDENT_TONE if (persona or '').lower().startswith('stu') else PRO_TONE
    return f"""You are BudgetBee, a helpful personal finance assistant.
    {tone}

    Given this monthly summary (INR):
    - Income: {summary['income']}
    - Total expenses: {summary['total_expenses']}
    - Savings (planned): {summary['savings_goal']}
    - Surplus (after expenses+savings): {summary['surplus']}
    - Top categories: {summary['top_categories']}

    Provide 5 short, tailored suggestions to improve savings next month.
    Keep it to numbered bullets.
    """

def make_qa_prompt(question: str, persona: str):
    tone = STUDENT_TONE if (persona or '').lower().startswith('stu') else PRO_TONE
    return f"""You are BudgetBee. {tone}
    Question: {question}
    Answer in 4 crisp bullets with one practical next step.
    """