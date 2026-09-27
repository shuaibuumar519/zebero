from database import get_conn
from datetime import datetime, timedelta


def get_contract_plans():
    conn = get_conn()
    try:
        rows = conn.execute(
            """
            SELECT *
            FROM contract_plans
            ORDER BY price ASC
            """
        ).fetchall()
    except Exception:
        rows = []
    conn.close()
    return rows


def get_plan(plan_id):
    conn = get_conn()
    row = conn.execute(
        """
        SELECT *
        FROM contract_plans
        WHERE id = ?
        """,
        (plan_id,),
    ).fetchone()
    conn.close()
    return row


def get_user_contracts(user_id):
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT
            user_contracts.*,
            contract_plans.name,
            contract_plans.price,
            contract_plans.daily_profit,
            contract_plans.duration_days
        FROM user_contracts
        JOIN contract_plans
            ON contract_plans.id = user_contracts.plan_id
        WHERE user_contracts.user_id = ?
        ORDER BY user_contracts.id DESC
        """,
        (user_id,),
    ).fetchall()
    conn.close()
    return rows


def create_contract(user_id, plan, quantity=1):
    conn = get_conn()

    plan_id = plan["id"]
    days = 30
    try:
        days = int(plan["duration_days"] or 30)
    except Exception:
        try:
            days = int(plan["duration"] or 30)
        except Exception:
            days = 30

    start = datetime.now()
    end = start + timedelta(days=days)

    conn.execute(
        """
        INSERT INTO user_contracts
        (user_id, plan_id, quantity, start_date, end_date, status)
        VALUES (?, ?, ?, ?, ?, 'active')
        """,
        (
            user_id,
            plan_id,
            quantity,
            start.isoformat(),
            end.isoformat(),
        ),
    )
    conn.commit()
    conn.close()
