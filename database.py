import os
import sqlite3

DATABASE_URL = os.environ.get("DATABASE_URL")
DATABASE = os.environ.get("DATABASE_PATH", "users.db")
IS_POSTGRES = bool(DATABASE_URL)


def get_conn():
    if IS_POSTGRES:
        import psycopg2
        from psycopg2.extras import RealDictCursor

        # Railway sometimes uses postgres:// 
        url = DATABASE_URL
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)

        conn = psycopg2.connect(url)
        return conn
    else:
        conn = sqlite3.connect(DATABASE)
        conn.row_factory = sqlite3.Row
        return conn


def _q(sql):
    """Convert SQLite ? placeholders to Postgres %s"""
    if IS_POSTGRES:
        return sql.replace("?", "%s")
    return sql


def init_db():
    conn = get_conn()
    cur = conn.cursor()

    if IS_POSTGRES:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                google_id TEXT UNIQUE,
                username TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                picture TEXT,
                referred_by TEXT,
                balance DOUBLE PRECISION DEFAULT 0,
                commission_balance DOUBLE PRECISION DEFAULT 0,
                referral_code TEXT UNIQUE,
                daily_day INTEGER DEFAULT 1,
                last_daily_claim TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                id SERIAL PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            INSERT INTO admins (id, username, password)
            VALUES (1, 'admin', 'admin123')
            ON CONFLICT (id) DO NOTHING
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id SERIAL PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                reward DOUBLE PRECISION NOT NULL,
                task_url TEXT NOT NULL,
                task_type TEXT NOT NULL,
                upgrade_level INTEGER DEFAULT 1,
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS daily_rewards (
                id SERIAL PRIMARY KEY,
                user_id INTEGER UNIQUE NOT NULL,
                current_day INTEGER DEFAULT 1,
                last_claim_date TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS contract_plans (
                id SERIAL PRIMARY KEY,
                name TEXT,
                price DOUBLE PRECISION,
                duration INTEGER,
                daily_profit DOUBLE PRECISION,
                status TEXT DEFAULT 'active'
            )
        """)
        cur.execute("SELECT COUNT(*) FROM contract_plans")
        row = cur.fetchone()
        count = row[0] if row else 0
        if count == 0:
            cur.execute("""
                INSERT INTO contract_plans (name, price, duration, daily_profit, status)
                VALUES
                ('Basic', 1000, 30, 50, 'active'),
                ('Silver', 3000, 30, 150, 'active'),
                ('Gold', 5000, 30, 300, 'active'),
                ('Diamond', 10000, 30, 700, 'active')
            """)
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
        cur.execute("""
            CREATE TABLE IF NOT EXISTS withdrawals (
                id SERIAL PRIMARY KEY,
                user_id INTEGER,
                account_id INTEGER,
                amount DOUBLE PRECISION,
                status TEXT DEFAULT 'pending',
                created_at TEXT
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS deposits (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                tx_ref TEXT UNIQUE NOT NULL,
                flw_ref TEXT,
                amount DOUBLE PRECISION NOT NULL,
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
        cur.execute("""
            CREATE TABLE IF NOT EXISTS task_history (
                id SERIAL PRIMARY KEY,
                user_id INTEGER,
                task_id INTEGER,
                reward DOUBLE PRECISION,
                claimed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        # SQLite fallback (local Termux)
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
        # ... sauran SQLite tables kamar da safe ...

    conn.commit()
    cur.close()
    conn.close()


def migrate_db():
    init_db()
