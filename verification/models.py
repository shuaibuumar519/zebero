from database import get_conn
from datetime import datetime

def connect():
    return get_conn()

def create_verification(
    user_id,
    task_id,
    screenshot,
    status="approved",
):
    conn = connect()

    conn.execute(
        """
        INSERT INTO task_verifications
        (
            user_id,
            task_id,
            screenshot,
            status,
            created_at
        )
        VALUES
        (?, ?, ?, ?, ?)
        """,
        (
            user_id,
            task_id,
            screenshot,
            status,
            datetime.now().isoformat(),
        ),
    )

    conn.commit()
    conn.close()


def has_verification(user_id, task_id):
    conn = connect()

    row = conn.execute(
        """
        SELECT *
        FROM task_verifications
        WHERE user_id=?
        AND task_id=?
        ORDER BY id DESC
        LIMIT 1
        """,
        (user_id, task_id),
    ).fetchone()

    conn.close()
    return row


def get_user_task_status(user_id, task_id):
    conn = connect()

    row = conn.execute(
        """
        SELECT status, created_at
        FROM task_verifications
        WHERE user_id=?
        AND task_id=?
        ORDER BY id DESC
        LIMIT 1
        """,
        (user_id, task_id),
    ).fetchone()

    conn.close()

    if row:
        return {
            "status": row["status"],
            "created_at": row["created_at"],
        }

    return None


def get_all_verifications():
    conn = connect()

    rows = conn.execute(
        """
        SELECT
            task_verifications.*,
            users.username,
            tasks.title
        FROM task_verifications
        JOIN users ON users.id = task_verifications.user_id
        JOIN tasks ON tasks.id = task_verifications.task_id
        ORDER BY task_verifications.id DESC
        """
    ).fetchall()

    conn.close()
    return rows


def get_verification(verification_id):
    conn = connect()

    row = conn.execute(
        """
        SELECT
            task_verifications.*,
            tasks.reward
        FROM task_verifications
        JOIN tasks ON tasks.id = task_verifications.task_id
        WHERE task_verifications.id = ?
        """,
        (verification_id,),
    ).fetchone()

    conn.close()
    return row


def update_verification_status(verification_id, status):
    conn = connect()

    conn.execute(
        """
        UPDATE task_verifications
        SET status = ?
        WHERE id = ?
        """,
        (status, verification_id),
    )

    conn.commit()
    conn.close()


def add_balance(user_id, amount):
    conn = connect()

    conn.execute(
        """
        UPDATE users
        SET balance = balance + ?
        WHERE id = ?
        """,
        (amount, user_id),
    )

    conn.commit()
    conn.close()
