from database import get_conn

def connect():
    return get_conn()

def get_user_contracts(user_id):

    conn = connect()

    contracts = conn.execute(
        """
        SELECT
            contract_plans.name,
            user_contracts.quantity
        FROM user_contracts
        JOIN contract_plans
        ON contract_plans.id=user_contracts.plan_id
        WHERE user_contracts.user_id=?
        AND user_contracts.status='active'
        """,
        (user_id,),
    ).fetchall()

    conn.close()

    return contracts


def get_upgrade_levels(user_id):

    contracts = get_user_contracts(user_id)

    levels = {}

    for c in contracts:

        levels[c["name"].lower()] = (
            levels.get(c["name"].lower(), 0)
            + c["quantity"]
        )

    return levels


def get_user_balance(user_id):

    conn = connect()

    user = conn.execute(
        "SELECT balance FROM users WHERE id=?",
        (user_id,),
    ).fetchone()

    conn.close()

    if user:
        return user["balance"]

    return 0


def deduct_balance(user_id, amount):

    conn = connect()

    conn.execute(
        """
        UPDATE users
        SET balance=balance-?
        WHERE id=?
        """,
        (
            amount,
            user_id,
        ),
    )

    conn.commit()
    conn.close()
def has_active_contract(user_id):

    conn = connect()

    contract = conn.execute(
        """
        SELECT 1
        FROM user_contracts
        WHERE user_id=?
        AND status='active'
        LIMIT 1
        """,
        (user_id,),
    ).fetchone()

    conn.close()

    return contract is not None
