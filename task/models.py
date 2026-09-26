from database import get_conn

def connect():
    return get_conn()

def init_task_history():

    conn = connect()

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS task_history(

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            user_id INTEGER NOT NULL,

            task_id INTEGER NOT NULL,

            reward REAL NOT NULL,

            claim_date TEXT NOT NULL
        )
        """
    )

    conn.commit()
    conn.close()


def already_claimed(user_id, task_id):

    conn = connect()

    row = conn.execute(
        """
        SELECT id
        FROM task_history
        WHERE user_id=?
        AND task_id=?
        AND claim_date=?
        """,
        (
            user_id,
            task_id,
            str(date.today()),
        ),
    ).fetchone()

    conn.close()

    return row is not None


def save_claim(
    user_id,
    task_id,
    reward,
):

    conn = connect()

    conn.execute(
        """
        INSERT INTO task_history
        (
            user_id,
            task_id,
            reward,
            claim_date
        )
        VALUES
        (?, ?, ?, ?)
        """,
        (
            user_id,
            task_id,
            reward,
            str(date.today()),
        ),
    )

    conn.commit()
    conn.close()


def add_balance(
    user_id,
    amount,
):

    conn = connect()

    conn.execute(
        """
        UPDATE users
        SET balance=balance+?
        WHERE id=?
        """,
        (
            amount,
            user_id,
        ),
    )

    conn.commit()
    conn.close()
def get_claim_count(user_id):

    conn = connect()

    total = conn.execute(
        """
        SELECT COUNT(*) AS total
        FROM task_history
        WHERE user_id=?
        """,
        (user_id,),
    ).fetchone()

    conn.close()

    return total["total"]
