from flask import render_template, session, redirect, request

from contract.models import (
    get_contract_plans,
    get_plan,
    create_contract,
)

from dailycheck.models import get_balance, update_balance


def upgrade_page():
    if "user" not in session:
        return redirect("/login")

    plans = get_contract_plans()
    return render_template(
        "upgrade/index.html",
        plans=plans,
        user=session.get("user"),
    )


def upgrade_buy_page():
    if "user" not in session:
        return redirect("/login")

    user_id = session["user"]["id"]
    plan_id = request.args.get("id")

    if plan_id:
        plan = get_plan(plan_id)
        plans = [dict(plan)] if plan else []
    else:
        plans = []

    if not plans:
        plans = [dict(p) for p in get_contract_plans()]

    balance = get_balance(user_id) or 0

    return render_template(
        "upgrade/buy.html",
        plans=plans,
        balance=balance,
    )


def check_upgrade():
    if "user" not in session:
        return redirect("/login")
    return redirect("/upgrade")
