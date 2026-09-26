from database import get_conn

def connect():
    return get_conn()

def create_withdrawal_tables():
    conn = get_db()

    # ==========================================
    # WITHDRAWAL ACCOUNTS
    # ==========================================

    conn.execute("""
        CREATE TABLE IF NOT EXISTS withdrawal_accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            bank_code TEXT NOT NULL,
            bank_name TEXT NOT NULL,
            account_number TEXT NOT NULL,
            account_name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, account_number)
        )
    """)

    # ==========================================
    # WITHDRAWALS
    # ==========================================

    conn.execute("""
        CREATE TABLE IF NOT EXISTS withdrawals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            account_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            fee REAL DEFAULT 0,
            total REAL NOT NULL,
            reference TEXT UNIQUE NOT NULL,
            flutterwave_ref TEXT,
            status TEXT DEFAULT 'pending',
            failure_reason TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            processed_at TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


# ==========================================
# SAVE BANK ACCOUNT
# ==========================================

def add_withdrawal_account(
    user_id,
    bank_code,
    bank_name,
    account_number,
    account_name,
):
    conn = get_db()

    try:
        cur = conn.execute("""
            INSERT INTO withdrawal_accounts (
                user_id,
                bank_code,
                bank_name,
                account_number,
                account_name
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            user_id,
            bank_code,
            bank_name,
            account_number,
            account_name,
        ))

        conn.commit()

        return cur.lastrowid

    except sqlite3.IntegrityError:
        return None

    finally:
        conn.close()


# ==========================================
# GET USER ACCOUNTS
# ==========================================

def get_withdrawal_accounts(user_id):
    conn = get_db()

    rows = conn.execute("""
        SELECT *
        FROM withdrawal_accounts
        WHERE user_id = ?
        ORDER BY id DESC
    """, (user_id,)).fetchall()

    conn.close()

    return rows


# ==========================================
# GET ONE ACCOUNT
# ==========================================

def get_withdrawal_account(
    account_id,
    user_id,
):
    conn = get_db()

    row = conn.execute("""
        SELECT *
        FROM withdrawal_accounts
        WHERE id = ?
          AND user_id = ?
        LIMIT 1
    """, (
        account_id,
        user_id,
    )).fetchone()

    conn.close()

    return row


# ==========================================
# DELETE ACCOUNT
# ==========================================

def delete_withdrawal_account(
    account_id,
    user_id,
):
    conn = get_db()

    cur = conn.execute("""
        DELETE FROM withdrawal_accounts
        WHERE id = ?
          AND user_id = ?
    """, (
        account_id,
        user_id,
    ))

    changed = cur.rowcount

    conn.commit()
    conn.close()

    return changed == 1


# ==========================================
# CREATE WITHDRAWAL
# ==========================================

def create_withdrawal(
    user_id,
    account_id,
    amount,
    fee,
    total,
    reference,
):
    conn = get_db()

    cur = conn.execute("""
        INSERT INTO withdrawals (
            user_id,
            account_id,
            amount,
            fee,
            total,
            reference,
            status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        user_id,
        account_id,
        float(amount),
        float(fee),
        float(total),
        reference,
        "pending",
    ))

    withdrawal_id = cur.lastrowid

    conn.commit()
    conn.close()

    return withdrawal_id


# ==========================================
# GET WITHDRAWAL
# ==========================================

def get_withdrawal(
    withdrawal_id,
    user_id=None,
):
    conn = get_db()

    if user_id is None:

        row = conn.execute("""
            SELECT *
            FROM withdrawals
            WHERE id = ?
            LIMIT 1
        """, (
            withdrawal_id,
        )).fetchone()

    else:

        row = conn.execute("""
            SELECT *
            FROM withdrawals
            WHERE id = ?
              AND user_id = ?
            LIMIT 1
        """, (
            withdrawal_id,
            user_id,
        )).fetchone()

    conn.close()

    return row


# ==========================================
# UPDATE WITHDRAWAL
# ==========================================

def update_withdrawal_status(
    withdrawal_id,
    status,
    flutterwave_ref=None,
    failure_reason=None,
):
    conn = get_db()

    conn.execute("""
        UPDATE withdrawals
        SET
            status = ?,
            flutterwave_ref = ?,
            failure_reason = ?,
            processed_at = ?
        WHERE id = ?
    """, (
        status,
        flutterwave_ref,
        failure_reason,
        datetime.now().isoformat(),
        withdrawal_id,
    ))

    conn.commit()
    conn.close()


# ==========================================
# USER WITHDRAWAL HISTORY
# ==========================================

def get_user_withdrawals(user_id):
    conn = get_db()

    rows = conn.execute("""
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
    """, (
        user_id,
    )).fetchall()

    conn.close()

    return rows
