from database import get_conn

def connect():
    return get_conn()

REWARDS = {
    1: 50,
    2: 100,
    3: 150,
    4: 200,
    5: 250,
    6: 300,
    7: 500,
}


def get_daily_data(user_id):
    conn = connect()

    user = conn.execute(
        """
        SELECT
            balance,
            daily_day,
            last_daily_claim
        FROM users
        WHERE id=?
        """,
        (user_id,),
    ).fetchone()

    conn.close()

    return user


def claim_daily(user_id):

    conn = connect()

    user = conn.execute(
        """
        SELECT
            balance,
            daily_day,
            last_daily_claim
        FROM users
        WHERE id=?
        """,
        (user_id,),
    ).fetchone()

    today = str(date.today())

    if user["last_daily_claim"] == today:
        conn.close()
        return False

    day = user["daily_day"] + 1

    if day > 7:
        day = 1

    reward = REWARDS[day]

    balance = user["balance"] + reward

    conn.execute(
        """
        UPDATE users
        SET
            balance=?,
            daily_day=?,
            last_daily_claim=?
        WHERE id=?
        """,
        (
            balance,
            day,
            today,
            user_id,
        ),
    )

    conn.commit()
    conn.close()

    return True
def get_balance(user_id):

    conn = connect()

    user = conn.execute(
        """
        SELECT balance
        FROM users
        WHERE id=?
        """,
        (user_id,),
    ).fetchone()

    conn.close()

    if user:
        return user["balance"]

    return 0


def update_balance(user_id, balance):

    conn = connect()

    conn.execute(
        """
        UPDATE users
        SET balance=?
        WHERE id=?
        """,
        (
            balance,
            user_id,
        ),
    )

    conn.commit()
    conn.close()
