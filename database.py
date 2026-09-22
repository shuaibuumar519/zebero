import os
import sqlite3

DATABASE = "users.db"
DATABASE_URL = os.getenv("DATABASE_URL")


def get_conn():
    """Postgres if DATABASE_URL set, else SQLite."""
    if DATABASE_URL and (
        DATABASE_URL.startswith("postgres://")
        or DATABASE_URL.startswith("postgresql://")
    ):
        import psycopg2

        url = DATABASE_URL
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        if "sslmode=" not in url:
            url += ("&" if "?" in url else "?") + "sslmode=require"
        return psycopg2.connect(url)

    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def _is_postgres(conn):
    return conn.__class__.__module__.startswith("psycopg2")


def init_db():
    conn = get_conn()
    is_pg = _is_postgres(conn)
    cur = conn.cursor()

    # ========== USERS ==========
    if is_pg:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                google_id TEXT UNIQUE,
                username TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                picture TEXT,
                referred_by TEXT,
                balance REAL DEFAULT 0,
                commission_balance REAL DEFAULT 0,
                referral_code TEXT UNIQUE,
                daily_day INTEGER DEFAULT 1,
                last_daily_claim TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                google_id TEXT UNIQUE,
                username TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                picture TEXT,
                referred_by TEXT,
                balance REAL DEFAULT 0,
                commission_balance REAL DEFAULT 0,
                referral_code TEXT UNIQUE,
                daily_day INTEGER DEFAULT 1,
                last_daily_claim TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

    # Migrate missing users columns
    if not is_pg:
        cur.execute("PRAGMA table_info(users)")
        cols = {row[1] for row in cur.fetchall()}
        for col, typ in [
            ("referred_by", "TEXT"),
            ("balance", "REAL DEFAULT 0"),
            ("commission_balance", "REAL DEFAULT 0"),
            ("referral_code", "TEXT"),
            ("daily_day", "INTEGER DEFAULT 1"),
            ("last_daily_claim", "TEXT"),
        ]:
            if col not in cols:
                try:
                    cur.execute(f"ALTER TABLE users ADD COLUMN {col} {typ}")
                except Exception:
                    pass
    else:
        for col, typ in [
            ("referred_by", "TEXT"),
            ("balance", "REAL DEFAULT 0"),
            ("commission_balance", "REAL DEFAULT 0"),
            ("referral_code", "TEXT"),
            ("daily_day", "INTEGER DEFAULT 1"),
            ("last_daily_claim", "TEXT"),
        ]:
            try:
                cur.execute(
                    f"ALTER TABLE users ADD COLUMN IF NOT EXISTS {col} {typ}"
                )
            except Exception:
                pass

    # ========== ADMINS ==========
    if is_pg:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                id SERIAL PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        """)

    # ========== TASKS ==========
    if is_pg:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id SERIAL PRIMARY KEY,
                title TEXT,
                reward REAL DEFAULT 0,
                task_type TEXT DEFAULT 'normal',
                upgrade_level TEXT,
                task_url TEXT,
                quantity INTEGER DEFAULT 1,
                status TEXT DEFAULT 'active'
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                reward REAL DEFAULT 0,
                task_type TEXT DEFAULT 'normal',
                upgrade_level TEXT,
                task_url TEXT,
                quantity INTEGER DEFAULT 1,
                status TEXT DEFAULT 'active'
            )
        """)

    # ========== TASK HISTORY ==========
    if is_pg:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS task_history (
                id SERIAL PRIMARY KEY,
                user_id INTEGER,
                task_id INTEGER,
                reward REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS task_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                task_id INTEGER,
                reward REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

    # ========== DEPOSITS ==========
    if is_pg:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS deposits (
                id SERIAL PRIMARY KEY,
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
    else:
        cur.execute("""
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

    # ========== WITHDRAWAL ACCOUNTS ==========
    if is_pg:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS withdrawal_accounts (
                id SERIAL PRIMARY KEY,
                user_id INTEGER,
                bank_name TEXT,
                account_number TEXT,
                account_name TEXT,
                bank_code TEXT
            )
        """)
    else:
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

    # ========== WITHDRAWALS ==========
    if is_pg:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS withdrawals (
                id SERIAL PRIMARY KEY,
                user_id INTEGER,
                account_id INTEGER,
                amount REAL,
                status TEXT DEFAULT 'pending',
                created_at TEXT
            )
        """)
    else:
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

    # ========== UPGRADE PLANS ==========
    if is_pg:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS upgrade_plans (
                id SERIAL PRIMARY KEY,
                name TEXT,
                price REAL,
                level TEXT,
                status TEXT DEFAULT 'active'
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS upgrade_plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                price REAL,
                level TEXT,
                status TEXT DEFAULT 'active'
            )
        """)

    # ========== USER UPGRADES ==========
    if is_pg:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS user_upgrades (
                id SERIAL PRIMARY KEY,
                user_id INTEGER,
                plan_id INTEGER,
                quantity INTEGER DEFAULT 1,
                status TEXT DEFAULT 'active'
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS user_upgrades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                plan_id INTEGER,
                quantity INTEGER DEFAULT 1,
                status TEXT DEFAULT 'active'
            )
        """)

    # ========== USER CONTRACTS ==========
    if is_pg:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS user_contracts (
                id SERIAL PRIMARY KEY,
                user_id INTEGER,
                plan_id INTEGER,
                quantity INTEGER DEFAULT 1,
                start_date TEXT,
                end_date TEXT,
                status TEXT DEFAULT 'active'
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS user_contracts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                plan_id INTEGER,
                quantity INTEGER DEFAULT 1,
                start_date TEXT,
                end_date TEXT,
                status TEXT DEFAULT 'active'
            )
        """)

    # ========== CONTRACT PLANS ==========
    if is_pg:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS contract_plans (
                id SERIAL PRIMARY KEY,
                name TEXT,
                price REAL,
                daily_profit REAL,
                duration_days INTEGER,
                status TEXT DEFAULT 'active'
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS contract_plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                price REAL,
                daily_profit REAL,
                duration_days INTEGER,
                status TEXT DEFAULT 'active'
            )
        """)

    # ========== SEED UPGRADE PLANS ==========
    cur.execute("SELECT COUNT(*) FROM upgrade_plans")
    row = cur.fetchone()
    count = row[0] if row else 0

    if count == 0:
        plans = [
            ("Basic", 1000, "basic"),
            ("Silver", 3000, "silver"),
            ("Gold", 5000, "gold"),
            ("Diamond", 10000, "diamond"),
        ]
        for name, price, level in plans:
            if is_pg:
                cur.execute(
                    """
                    INSERT INTO upgrade_plans (name, price, level, status)
                    VALUES (%s, %s, %s, 'active')
                    """,
                    (name, price, level),
                )
            else:
                cur.execute(
                    """
                    INSERT INTO upgrade_plans (name, price, level, status)
                    VALUES (?, ?, ?, 'active')
                    """,
                    (name, price, level),
                )

    # ========== SEED CONTRACT PLANS ==========
    cur.execute("SELECT COUNT(*) FROM contract_plans")
    row = cur.fetchone()
    count = row[0] if row else 0

    if count == 0:
        contracts = [
            ("Silver", 5000, 250, 30),
            ("Gold", 10000, 600, 30),
            ("Diamond", 20000, 1500, 30),
        ]
        for name, price, daily, days in contracts:
            if is_pg:
                cur.execute(
                    """
                    INSERT INTO contract_plans
                    (name, price, daily_profit, duration_days, status)
                    VALUES (%s, %s, %s, %s, 'active')
                    """,
                    (name, price, daily, days),
                )
            else:
                cur.execute(
                    """
                    INSERT INTO contract_plans
                    (name, price, daily_profit, duration_days, status)
                    VALUES (?, ?, ?, ?, 'active')
                    """,
                    (name, price, daily, days),
                )

    conn.commit()
    cur.close()
    conn.close()


def migrate_db():
    """Alias used by app.py"""
    init_db()
