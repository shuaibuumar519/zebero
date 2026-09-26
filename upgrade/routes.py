from flask import render_template, session, redirect, request

from contract.models import (
    get_contract_plans,
    get_plan,
    create_contract,
)

from dailycheck.models import (
    get_balance,
    update_balance,
)


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
        rows = get_contract_plans()
        plans = [dict(r) for r in rows]

    balance = get_balance(user_id) or 0

    return render_template(
        "upgrade/buy.html",
        plans=plans,
        balance=balance,
    )


def buy_contract():
    if "user" not in session:
        return redirect("/login")

    plan_id = request.args.get("id")
    quantity = int(request.args.get("quantity", 1) or 1)

    if quantity < 1:
        quantity = 1
    if quantity > 10:
        quantity = 10

    if not plan_id:
        return redirect("/upgrade")

    plan = get_plan(plan_id)
    if not plan:
        return redirect("/upgrade")

    user_id = session["user"]["id"]
    balance = get_balance(user_id) or 0
    total = float(plan["price"]) * quantity

    if balance < total:
        return redirect("/upgrade/buy?id=" + str(plan_id))

    update_balance(user_id, balance - total)
    create_contract(user_id, plan, quantity)

    return redirect("/upgrade")
