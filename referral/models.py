from database import get_conn
import secrets
import string

def connect():
    return get_conn()

def ensure_commission_column():
    conn = connect()
    try:
        conn.execute(
            "ALTER TABLE users ADD COLUMN commission_balance REAL DEFAULT 0"
        )
        conn.commit()
    except Exception:
        pass
    conn.close()


ensure_commission_column()


def generate_referral_code(length=8):
    chars = string.ascii_uppercase + string.digits
    while True:
        code = "".join(secrets.choice(chars) for _ in range(length))
        conn = connect()
        row = conn.execute(
            "SELECT id FROM users WHERE referral_code=?",
            (code,),
        ).fetchone()
        conn.close()
        if row is None:
            return code


def create_referral_code(user_id):
    conn = connect()
    user = conn.execute(
        "SELECT referral_code FROM users WHERE id=?",
        (user_id,),
    ).fetchone()
    if user and user["referral_code"]:
        conn.close()
        return user["referral_code"]
    code = generate_referral_code()
    conn.execute(
        "UPDATE users SET referral_code=? WHERE id=?",
        (code, user_id),
    )
    conn.commit()
    conn.close()
    return code


def get_referral_code(user_id):
    conn = connect()
    user = conn.execute(
        "SELECT referral_code FROM users WHERE id=?",
        (user_id,),
    ).fetchone()
    conn.close()
    if user:
        return user["referral_code"]
    return None


def count_referrals(referral_code):
    conn = connect()
    total = conn.execute(
        "SELECT COUNT(*) FROM users WHERE referred_by=?",
        (referral_code,),
    ).fetchone()[0]
    conn.close()
    return total


def get_user_by_referral_code(code):
    if not code:
        return None
    conn = connect()
    user = conn.execute(
        "SELECT * FROM users WHERE referral_code=?",
        (code.strip().upper(),),
    ).fetchone()
    conn.close()
    return user


def add_balance(user_id, amount):
    conn = connect()
    conn.execute(
        "UPDATE users SET balance = COALESCE(balance, 0) + ? WHERE id=?",
        (float(amount), user_id),
    )
    conn.commit()
    conn.close()


def add_commission(user_id, amount):
    """Ƙara ga balance + commission_balance (wanda kawai za a iya withdraw)"""
    conn = connect()
    conn.execute(
        """
        UPDATE users
        SET balance = COALESCE(balance, 0) + ?,
            commission_balance = COALESCE(commission_balance, 0) + ?
        WHERE id=?
        """,
        (float(amount), float(amount), user_id),
    )
    conn.commit()
    conn.close()


def get_commission_balance(user_id):
    conn = connect()
    row = conn.execute(
        "SELECT COALESCE(commission_balance, 0) AS cb FROM users WHERE id=?",
        (user_id,),
    ).fetchone()
    conn.close()
    if row:
        return float(row["cb"] or 0)
    return 0.0


def deduct_commission(user_id, amount):
    """Cire daga balance da commission_balance"""
    conn = connect()
    conn.execute(
        """
        UPDATE users
        SET balance = COALESCE(balance, 0) - ?,
            commission_balance = COALESCE(commission_balance, 0) - ?
        WHERE id=?
          AND COALESCE(commission_balance, 0) >= ?
        """,
        (float(amount), float(amount), user_id, float(amount)),
    )
    changed = conn.total_changes
    conn.commit()
    conn.close()
    return changed > 0


def give_signup_bonus(referrer_id, new_user_id, bonus=500):
    """Signup bonus yana shiga balance kawai — ba commission ba (ba za a iya withdraw ba)"""
    add_balance(referrer_id, bonus)
    add_balance(new_user_id, bonus)


def give_deposit_commission(depositor_id, deposit_amount, percent=30):
    """
    30% commission → balance + commission_balance
    (kawai wannan shine za a iya withdraw)
    """
    conn = connect()
    user = conn.execute(
        "SELECT referred_by FROM users WHERE id=?",
        (depositor_id,),
    ).fetchone()
    if not user or not user["referred_by"]:
        conn.close()
        return False
    referrer = conn.execute(
        "SELECT id FROM users WHERE referral_code=?",
        (user["referred_by"],),
    ).fetchone()
    conn.close()
    if not referrer:
        return False
    commission = float(deposit_amount) * (percent / 100.0)
    if commission <= 0:
        return False
    add_commission(referrer["id"], commission)
    return True
