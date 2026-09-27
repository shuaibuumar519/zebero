from database import get_conn
from datetime import datetime


def create_withdrawal_tables():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS withdrawal_accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            bank_name TEXT,
            account_number TEXT,
            account_name TEXT,
            bank_code TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS withdrawals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            account_id INTEGER,
            amount REAL,
            status TEXT DEFAULT 'pending',
            created_at TEXT
        )
    """)

    conn.commit()
    conn.close()


def get_withdrawal_accounts(user_id):
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT *
        FROM withdrawal_accounts
        WHERE user_id = ?
        ORDER BY id DESC
        """,
        (user_id,),
    ).fetchall()
    conn.close()
    return rows


def get_withdrawal_account(account_id, user_id=None):
    conn = get_conn()
    if user_id is not None:
        row = conn.execute(
            """
            SELECT *
            FROM withdrawal_accounts
            WHERE id = ? AND user_id = ?
            """,
            (account_id, user_id),
        ).fetchone()
    else:
        row = conn.execute(
            """
            SELECT *
            FROM withdrawal_accounts
            WHERE id = ?
            """,
            (account_id,),
        ).fetchone()
    conn.close()
    return row


def add_withdrawal_account(
    user_id,
    bank_name,
    account_number,
    account_name,
    bank_code,
):
    conn = get_conn()
    conn.execute(
        """
        INSERT INTO withdrawal_accounts
        (user_id, bank_name, account_number, account_name, bank_code)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            user_id,
            bank_name,
            account_number,
            account_name,
            bank_code,
        ),
    )
    conn.commit()
    conn.close()


def create_withdrawal(user_id, account_id, amount):
    conn = get_conn()
    cur = conn.execute(
        """
        INSERT INTO withdrawals
        (user_id, account_id, amount, status, created_at)
        VALUES (?, ?, ?, 'pending', ?)
        """,
        (
            user_id,
            account_id,
            amount,
            datetime.now().isoformat(),
        ),
    )
    try:
        withdrawal_id = cur.lastrowid
    except Exception:
        withdrawal_id = None
    conn.commit()
    conn.close()
    return withdrawal_id


def update_withdrawal_status(withdrawal_id, status):
    conn = get_conn()
    conn.execute(
        """
        UPDATE withdrawals
        SET status = ?
        WHERE id = ?
        """,
        (status, withdrawal_id),
    )
    conn.commit()
    conn.close()


def get_user_withdrawals(user_id):
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT
            w.*,
            a.bank_name,
            a.account_number,
            a.account_name
        FROM withdrawals w
        JOIN withdrawal_accounts a
            ON a.id = w.account_id
        WHERE w.user_id = ?
        ORDER BY w.id DESC
        """,
        (user_id,),
    ).fetchall()
    conn.close()
    return rows
