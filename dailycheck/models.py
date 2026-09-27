from database import get_conn
from datetime import date


REWARDS = [50, 100, 150, 200, 250, 300, 500]  # Day 1 .. Day 7


def get_balance(user_id):
    conn = get_conn()
    row = conn.execute(
        """
        SELECT COALESCE(balance, 0) AS balance
        FROM users
        WHERE id = ?
        """,
        (user_id,),
    ).fetchone()
    conn.close()
    if not row:
        return 0
    try:
        return float(row["balance"])
    except Exception:
        return float(row[0] or 0)


def update_balance(user_id, new_balance):
    conn = get_conn()
    conn.execute(
        """
        UPDATE users
        SET balance = ?
        WHERE id = ?
        """,
        (new_balance, user_id),
    )
    conn.commit()
    conn.close()


def get_daily_data(user_id):
    conn = get_conn()
    user = conn.execute(
        """
        SELECT *
        FROM users
        WHERE id = ?
        """,
        (user_id,),
    ).fetchone()
    conn.close()

    if not user:
        return {
            "daily_day": 1,
            "last_daily_claim": None,
        }

    try:
        day = user["daily_day"]
    except Exception:
        day = 1

    if day is None or day < 1:
        day = 1
    if day > 7:
        day = 1

    try:
        last = user["last_daily_claim"]
    except Exception:
        last = None

    return {
        "daily_day": day,
        "last_daily_claim": last,
    }


def claim_daily(user_id):
    conn = get_conn()
    today = str(date.today())

    user = conn.execute(
        """
        SELECT *
        FROM users
        WHERE id = ?
        """,
        (user_id,),
    ).fetchone()

    if not user:
        conn.close()
        return False

    try:
        last = user["last_daily_claim"]
    except Exception:
        last = None

    try:
        day = user["daily_day"]
    except Exception:
        day = 1

    if day is None or day < 1:
        day = 1
    if day > 7:
        day = 1

    # an riga an claim yau
    if last == today:
        conn.close()
        return False

    # reward na Day 1 = REWARDS[0], Day 2 = REWARDS[1], ...
    reward = REWARDS[day - 1]

    conn.execute(
        """
        UPDATE users
        SET balance = COALESCE(balance, 0) + ?
        WHERE id = ?
        """,
        (reward, user_id),
    )

    # gobe: kara rana (bayan an biya ranar yanzu)
    next_day = day + 1
    if next_day > 7:
        next_day = 1

    conn.execute(
        """
        UPDATE users
        SET last_daily_claim = ?,
            daily_day = ?
        WHERE id = ?
        """,
        (today, next_day, user_id),
    )

    conn.commit()
    conn.close()
    return True
