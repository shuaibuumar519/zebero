from database import get_conn

def connect():
    return get_conn()

def get_contract_plans():

    conn = connect()

    plans = conn.execute(
        """
        SELECT *
        FROM contract_plans
        WHERE status='active'
        ORDER BY price ASC
        """
    ).fetchall()

    conn.close()

    return plans


def get_plan(plan_id):

    conn = connect()

    plan = conn.execute(
        """
        SELECT *
        FROM contract_plans
        WHERE id=?
        """,
        (plan_id,),
    ).fetchone()

    conn.close()

    return plan


def get_user_contracts(user_id):

    conn = connect()

    contracts = conn.execute(
        """
        SELECT
            user_contracts.*,
            contract_plans.name
        FROM user_contracts
        JOIN contract_plans
        ON contract_plans.id=user_contracts.plan_id
        WHERE user_contracts.user_id=?
        ORDER BY user_contracts.id DESC
        """,
        (user_id,),
    ).fetchall()

    conn.close()

    return contracts


def create_contract(

    user_id,
    plan,
    quantity=1,

):

    conn = connect()

    total_amount = plan["price"] * quantity
    total_daily_profit = plan["daily_profit"] * quantity

    conn.execute(
        """
        INSERT INTO user_contracts
        (
            user_id,
            plan_id,
            amount,
            daily_profit,
            duration,
            start_date,
            quantity
        )
        VALUES
        (
            ?, ?, ?, ?, ?, DATE('now'), ?
        )
        """,
        (
            user_id,
            plan["id"],
            total_amount,
            total_daily_profit,
            plan["duration"],
            quantity,
        ),
    )

    conn.commit()
    conn.close()
