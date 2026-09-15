import sqlite3

DATABASE = "users.db"


def init_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # ==========================================
    # USERS
    # ==========================================

    cursor.execute("""
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

    cursor.execute("PRAGMA table_info(users)")
    user_columns = {row[1] for row in cursor.fetchall()}

    if "referred_by" not in user_columns:
        cursor.execute("ALTER TABLE users ADD COLUMN referred_by TEXT")

    if "balance" not in user_columns:
        cursor.execute("ALTER TABLE users ADD COLUMN balance REAL DEFAULT 0")

    if "commission_balance" not in user_columns:
        cursor.execute(
            "ALTER TABLE users ADD COLUMN commission_balance REAL DEFAULT 0"
        )

    if "referral_code" not in user_columns:
        cursor.execute("ALTER TABLE users ADD COLUMN referral_code TEXT")

    if "daily_day" not in user_columns:
        cursor.execute(
            "ALTER TABLE users ADD COLUMN daily_day INTEGER DEFAULT 1"
        )

    if "last_daily_claim" not in user_columns:
        cursor.execute(
            "ALTER TABLE users ADD COLUMN last_daily_claim TEXT"
        )

    # ==========================================
    # ADMINS
    # ==========================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        INSERT OR IGNORE INTO admins (id, username, password)
        VALUES (1, 'admin', 'admin123')
    """)

    # ==========================================
    # TASKS
    # ==========================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            reward REAL NOT NULL,
            task_url TEXT NOT NULL,
            task_type TEXT NOT NULL,
            upgrade_level INTEGER DEFAULT 1,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("PRAGMA table_info(tasks)")
    task_columns = {row[1] for row in cursor.fetchall()}

    if "upgrade_level" not in task_columns:
        cursor.execute(
            "ALTER TABLE tasks ADD COLUMN upgrade_level INTEGER DEFAULT 1"
        )

    # ==========================================
    # DAILY REWARDS
    # ==========================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_rewards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE NOT NULL,
            current_day INTEGER DEFAULT 1,
            last_claim_date TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)

    # ==========================================
    # CONTRACT / UPGRADE PLANS
    # ==========================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS contract_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            price REAL,
            duration INTEGER,
            daily_profit REAL,
            status TEXT DEFAULT 'active'
        )
    """)

    cursor.execute("PRAGMA table_info(contract_plans)")
    plan_cols = {row[1] for row in cursor.fetchall()}

    if "daily_profit" not in plan_cols:
        try:
            cursor.execute(
                "ALTER TABLE contract_plans ADD COLUMN daily_profit REAL DEFAULT 0"
            )
        except Exception:
            pass

    cursor.execute("SELECT COUNT(*) FROM contract_plans")
    if cursor.fetchone()[0] == 0:
        cursor.executemany(
            """
            INSERT INTO contract_plans
            (name, price, duration, daily_profit, status)
            VALUES (?, ?, ?, ?, 'active')
            """,
            [
                ("Basic", 1000, 30, 50),
                ("Silver", 3000, 30, 150),
                ("Gold", 5000, 30, 300),
                ("Diamond", 10000, 30, 700),
            ],
        )

    cursor.execute("""
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

    # ==========================================
    # WITHDRAW
    # ==========================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS withdrawal_accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            bank_name TEXT,
            account_number TEXT,
            account_name TEXT,
            bank_code TEXT
        )
    """)

    cursor.execute("""
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


def migrate_db():
    init_db()
