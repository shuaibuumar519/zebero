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

from database import get_conn


def upgrade_page():
    if "user" not in session:
        return redirect("/login")

    # seed if empty (same as buy)
    _ensure_contract_plans()

    plans = get_contract_plans()
    return render_template(
        "upgrade/index.html",
        plans=plans,
        user=session.get("user"),
    )


def _ensure_contract_plans():
    conn = get_conn()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS contract_plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                price REAL,
                daily_profit REAL,
                duration_days INTEGER,
                status TEXT DEFAULT 'active'
            )
        """)
        row = conn.execute(
            "SELECT COUNT(*) AS c FROM contract_plans"
        ).fetchone()
        try:
            count = row["c"]
        except Exception:
            count = row[0] if row else 0

        if not count:
            for name, price, daily, days in [
                ("Basic", 1000, 150, 30),
                ("Silver", 5000, 800, 30),
                ("Gold", 10000, 1700, 30),
                ("Diamond", 50000, 9000, 30),
            ]:
                conn.execute(
                    """
                    INSERT INTO contract_plans
                    (name, price, daily_profit, duration_days, status)
                    VALUES (?, ?, ?, ?, 'active')
                    """,
                    (name, price, daily, days),
                )
            conn.commit()
    except Exception as e:
        print("ensure_contract_plans:", e)
    finally:
        conn.close()


def upgrade_buy_page():
    if "user" not in session:
        return redirect("/login")

    user_id = session["user"]["id"]
    _ensure_contract_plans()

    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM contract_plans ORDER BY price ASC"
    ).fetchall()
    conn.close()

    plans = []
    for r in rows:
        plans.append({
            "id": r["id"],
            "name": r["name"],
            "price": float(r["price"] or 0),
            "daily_profit": float(r["daily_profit"] or 0),
            "duration_days": int(r["duration_days"] or 30),
        })

    try:
        balance = get_balance(user_id) or 0
    except Exception:
        balance = 0

    return render_template(
        "upgrade/buy.html",
        plans=plans,
        balance=balance,
    )


def check_upgrade():
    if "user" not in session:
        return redirect("/login")
    return redirect("/upgrade")


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
