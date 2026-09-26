from database import get_conn

def connect():
    return get_conn()

def create_deposit_table():
    conn = get_db()

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

    conn = get_db()

    cur = conn.execute("""
        INSERT INTO deposits (
            user_id,
            tx_ref,
            amount,
            currency,
            status,
            expires_at
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        user_id,
        tx_ref,
        float(amount),
        "NGN",
        "pending",
        expires_at.isoformat(),
    ))

    deposit_id = cur.lastrowid
    conn.commit()
    conn.close()

    return {
        "id": deposit_id,
        "tx_ref": tx_ref,
        "expires_at": expires_at,
    }


def get_deposit(tx_ref):
    conn = get_db()
    row = conn.execute("""
        SELECT *
        FROM deposits
        WHERE tx_ref = ?
        LIMIT 1
    """, (tx_ref,)).fetchone()
    conn.close()
    return row


def save_virtual_account(tx_ref, account_number, bank_name, account_name=None):
    conn = get_db()
    cur = conn.execute("""
        UPDATE deposits
        SET
            account_number = ?,
            bank_name = ?,
            account_name = ?
        WHERE tx_ref = ?
    """, (account_number, bank_name, account_name, tx_ref))
    changed = cur.rowcount
    conn.commit()
    conn.close()
    return changed == 1


def expire_deposit_if_needed(tx_ref):
    conn = get_db()
    cur = conn.execute("""
        UPDATE deposits
        SET status = 'expired'
        WHERE tx_ref = ?
          AND status = 'pending'
          AND expires_at IS NOT NULL
          AND datetime(expires_at) <= datetime('now')
    """, (tx_ref,))
    changed = cur.rowcount
    conn.commit()
    conn.close()
    return changed == 1


def complete_deposit(tx_ref, flw_ref):
    """
    Atomically:
    1. Check deposit
    2. Check user
    3. Mark deposit successful
    4. Credit user balance
    5. Give 30% referral commission
    """
    conn = get_db()

    try:
        conn.execute("BEGIN IMMEDIATE")

        deposit = conn.execute("""
            SELECT *
            FROM deposits
            WHERE tx_ref = ?
            LIMIT 1
        """, (tx_ref,)).fetchone()

        if not deposit:
            conn.rollback()
            return {
                "success": False,
                "message": "Deposit not found.",
            }

        if deposit["status"] == "successful":
            conn.rollback()

            user = conn.execute("""
                SELECT balance
                FROM users
                WHERE id = ?
                LIMIT 1
            """, (deposit["user_id"],)).fetchone()

            return {
                "success": True,
                "already_completed": True,
                "amount": float(deposit["amount"]),
                "new_balance": (
                    float(user["balance"] or 0)
                    if user else None
                ),
            }

        if deposit["status"] != "pending":
            conn.rollback()
            return {
                "success": False,
                "message": f"Deposit status is {deposit['status']}.",
            }

        if deposit["expires_at"]:
            try:
                expires_at = datetime.fromisoformat(str(deposit["expires_at"]))
                if datetime.now() >= expires_at:
                    conn.execute("""
                        UPDATE deposits
                        SET status = 'expired'
                        WHERE tx_ref = ?
                          AND status = 'pending'
                    """, (tx_ref,))
                    conn.commit()
                    return {
                        "success": False,
                        "message": "Deposit has expired.",
                    }
            except (ValueError, TypeError):
                pass

        user = conn.execute("""
            SELECT id, balance
            FROM users
            WHERE id = ?
            LIMIT 1
        """, (deposit["user_id"],)).fetchone()

        if not user:
            conn.rollback()
            return {
                "success": False,
                "message": "User not found.",
            }

        amount = float(deposit["amount"])
        old_balance = float(user["balance"] or 0)
        new_balance = old_balance + amount

        cur = conn.execute("""
            UPDATE deposits
            SET
                status = 'successful',
                flw_ref = ?,
                paid_at = CURRENT_TIMESTAMP
            WHERE tx_ref = ?
              AND status = 'pending'
        """, (flw_ref, tx_ref))

        if cur.rowcount != 1:
            conn.rollback()
            return {
                "success": False,
                "message": "Deposit was already processed.",
            }

        cur = conn.execute("""
            UPDATE users
            SET balance = ?
            WHERE id = ?
        """, (new_balance, deposit["user_id"]))

        if cur.rowcount != 1:
            conn.rollback()
            return {
                "success": False,
                "message": "Could not update user balance.",
            }

        conn.commit()

        # 30% referral commission
        try:
            from referral.models import give_deposit_commission
            give_deposit_commission(
                depositor_id=deposit["user_id"],
                deposit_amount=amount,
                percent=30,
            )
        except Exception as e:
            print("Referral commission error:", e)

        return {
            "success": True,
            "already_completed": False,
            "amount": amount,
            "old_balance": old_balance,
            "new_balance": new_balance,
        }

    except Exception as e:
        conn.rollback()
        return {
            "success": False,
            "message": str(e),
        }

    finally:
        conn.close()


def get_user_deposits(user_id):
    conn = get_db()
    rows = conn.execute("""
        SELECT *
        FROM deposits
        WHERE user_id = ?
        ORDER BY id DESC
    """, (user_id,)).fetchall()
    conn.close()
    return rows


def get_deposit_by_flw_ref(flw_ref):
    conn = get_db()
    row = conn.execute("""
        SELECT *
        FROM deposits
        WHERE flw_ref = ?
        LIMIT 1
    """, (flw_ref,)).fetchone()
    conn.close()
    return row


def cancel_deposit(tx_ref):
    conn = get_db()
    cur = conn.execute("""
        UPDATE deposits
        SET status = 'cancelled'
        WHERE tx_ref = ?
          AND status = 'pending'
    """, (tx_ref,))
    changed = cur.rowcount
    conn.commit()
    conn.close()
    return changed == 1
