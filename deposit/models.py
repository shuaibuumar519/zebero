from database import get_conn
import uuid
from datetime import datetime, timedelta


def create_deposit_table():
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS deposits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            tx_ref TEXT UNIQUE NOT NULL,
            flw_ref TEXT,
            amount REAL NOT NULL,
            currency TEXT DEFAULT 'NGN',
            account_number TEXT,
            bank_name TEXT,
            account_name TEXT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP,
            paid_at TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def create_deposit(user_id, amount):
    tx_ref = "ZEBERO-" + uuid.uuid4().hex[:20].upper()
    expires_at = datetime.now() + timedelta(minutes=10)

    conn = get_conn()
    cur = conn.execute(
        """
        INSERT INTO deposits (
            user_id,
            tx_ref,
            amount,
            currency,
            status,
            expires_at
        )
        VALUES (?, ?, ?, 'NGN', 'pending', ?)
        """,
        (
            user_id,
            tx_ref,
            float(amount),
            expires_at.isoformat(),
        ),
    )
    try:
        deposit_id = cur.lastrowid
    except Exception:
        deposit_id = None
    conn.commit()
    conn.close()

    return {
        "id": deposit_id,
        "tx_ref": tx_ref,
        "amount": float(amount),
        "expires_at": expires_at.isoformat(),
    }


def save_virtual_account(
    tx_ref,
    account_number,
    bank_name,
    account_name,
    flw_ref=None,
):
    conn = get_conn()
    conn.execute(
        """
        UPDATE deposits
        SET account_number = ?,
            bank_name = ?,
            account_name = ?,
            flw_ref = COALESCE(?, flw_ref)
        WHERE tx_ref = ?
        """,
        (
            account_number,
            bank_name,
            account_name,
            flw_ref,
            tx_ref,
        ),
    )
    conn.commit()
    conn.close()


def get_deposit(tx_ref=None, deposit_id=None):
    conn = get_conn()
    if tx_ref:
        row = conn.execute(
            """
            SELECT *
            FROM deposits
            WHERE tx_ref = ?
            """,
            (tx_ref,),
        ).fetchone()
    elif deposit_id:
        row = conn.execute(
            """
            SELECT *
            FROM deposits
            WHERE id = ?
            """,
            (deposit_id,),
        ).fetchone()
    else:
        row = None
    conn.close()
    return row


def expire_deposit_if_needed(tx_ref):
    conn = get_conn()
    row = conn.execute(
        """
        SELECT *
        FROM deposits
        WHERE tx_ref = ?
        """,
        (tx_ref,),
    ).fetchone()

    if not row:
        conn.close()
        return None

    status = row["status"] if "status" in row.keys() else row[9]
    expires_at = row["expires_at"] if "expires_at" in row.keys() else None

    if status == "pending" and expires_at:
        try:
            exp = datetime.fromisoformat(str(expires_at))
            if datetime.now() > exp:
                conn.execute(
                    """
                    UPDATE deposits
                    SET status = 'expired'
                    WHERE tx_ref = ?
                    """,
                    (tx_ref,),
                )
                conn.commit()
                row = conn.execute(
                    """
                    SELECT *
                    FROM deposits
                    WHERE tx_ref = ?
                    """,
                    (tx_ref,),
                ).fetchone()
        except Exception:
            pass

    conn.close()
    return row


def complete_deposit(tx_ref, flw_ref=None):
    conn = get_conn()
    row = conn.execute(
        """
        SELECT *
        FROM deposits
        WHERE tx_ref = ?
        """,
        (tx_ref,),
    ).fetchone()

    if not row:
        conn.close()
        return False

    status = row["status"]
    if status == "successful":
        conn.close()
        return True

    user_id = row["user_id"]
    amount = float(row["amount"])

    conn.execute(
        """
        UPDATE deposits
        SET status = 'successful',
            flw_ref = COALESCE(?, flw_ref),
            paid_at = ?
        WHERE tx_ref = ?
        """,
        (
            flw_ref,
            datetime.now().isoformat(),
            tx_ref,
        ),
    )

    conn.execute(
        """
        UPDATE users
        SET balance = COALESCE(balance, 0) + ?
        WHERE id = ?
        """,
        (amount, user_id),
    )

    # Referral commission 30% on deposit (if referred_by set)
    try:
        user = conn.execute(
            """
            SELECT referred_by
            FROM users
            WHERE id = ?
            """,
            (user_id,),
        ).fetchone()

        if user and user["referred_by"]:
            ref_code = user["referred_by"]
            referrer = conn.execute(
                """
                SELECT id, COALESCE(commission_balance, 0) AS commission_balance
                FROM users
                WHERE referral_code = ?
                """,
                (ref_code,),
            ).fetchone()

            if referrer:
                commission = amount * 0.30
                conn.execute(
                    """
                    UPDATE users
                    SET commission_balance = COALESCE(commission_balance, 0) + ?,
                        balance = COALESCE(balance, 0) + ?
                    WHERE id = ?
                    """,
                    (commission, commission, referrer["id"]),
                )
    except Exception:
        pass

    conn.commit()
    conn.close()
    return True


def get_user_deposits(user_id, limit=20):
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT *
        FROM deposits
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT ?
        """,
        (user_id, limit),
    ).fetchall()
    conn.close()
    return rows
