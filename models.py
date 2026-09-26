from database import get_conn

def connect():
    return get_conn()

# ==========================
# USERS
# ==========================

def create_user(
    google_id,
    username,
    email,
    picture,
    referred_by=None,
):
    conn = connect()

    conn.execute(
        """
        INSERT INTO users
        (
            google_id,
            username,
            email,
            picture,
            referred_by,
            balance
        )
        VALUES
        (?, ?, ?, ?, ?, ?)
        """,
        (
            google_id,
            username,
            email,
            picture,
            referred_by,
            0,
        ),
    )

    conn.commit()
    conn.close()


def get_user_by_google_id(google_id):
    conn = connect()

    user = conn.execute(
        """
        SELECT *
        FROM users
        WHERE google_id=?
        """,
        (google_id,),
    ).fetchone()

    conn.close()
    return user


def get_user_by_email(email):
    conn = connect()

    user = conn.execute(
        """
        SELECT *
        FROM users
        WHERE email=?
        """,
        (email,),
    ).fetchone()

    conn.close()
    return user


def get_user(user_id):
    conn = connect()

    user = conn.execute(
        """
        SELECT *
        FROM users
        WHERE id=?
        """,
        (user_id,),
    ).fetchone()

    conn.close()
    return user


def get_all_users():
    conn = connect()

    users = conn.execute(
        """
        SELECT *
        FROM users
        ORDER BY id DESC
        """
    ).fetchall()

    conn.close()
    return users


# ==========================
# TASKS
# ==========================

def create_task(
    title,
    description,
    reward,
    task_url,
    task_type,
    upgrade_level,
):
    conn = connect()

    conn.execute(
        """
        INSERT INTO tasks
        (
            title,
            description,
            reward,
            task_url,
            task_type,
            upgrade_level,
            status
        )
        VALUES
        (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            title,
            description,
            reward,
            task_url,
            task_type,
            upgrade_level,
            "active",
        ),
    )

    conn.commit()
    conn.close()


def get_all_tasks():
    conn = connect()

    tasks = conn.execute(
        """
        SELECT *
        FROM tasks
        ORDER BY id DESC
        """
    ).fetchall()

    conn.close()
    return tasks


def get_task(task_id):
    conn = connect()

    task = conn.execute(
        """
        SELECT *
        FROM tasks
        WHERE id=?
        """,
        (task_id,),
    ).fetchone()

    conn.close()
    return task


def update_task(
    task_id,
    title,
    description,
    reward,
    task_url,
    task_type,
    upgrade_level,
    status,
):
    conn = connect()

    conn.execute(
        """
        UPDATE tasks
        SET
            title=?,
            description=?,
            reward=?,
            task_url=?,
            task_type=?,
            upgrade_level=?,
            status=?
        WHERE id=?
        """,
        (
            title,
            description,
            reward,
            task_url,
            task_type,
            upgrade_level,
            status,
            task_id,
        ),
    )

    conn.commit()
    conn.close()


def delete_task(task_id):
    conn = connect()

    conn.execute(
        """
        DELETE FROM tasks
        WHERE id=?
        """,
        (task_id,),
    )

    conn.commit()
    conn.close()


def get_tasks_by_type(task_type, upgrade_level=None):
    conn = connect()

    if task_type == "normal":
        tasks = conn.execute(
            """
            SELECT *
            FROM tasks
            WHERE task_type='normal'
            AND status='active'
            ORDER BY id DESC
            """
        ).fetchall()

    elif task_type == "upgrade":
        tasks = conn.execute(
            """
            SELECT *
            FROM tasks
            WHERE task_type='upgrade'
            AND upgrade_level=?
            AND status='active'
            ORDER BY id DESC
            """,
            (upgrade_level,),
        ).fetchall()

    else:
        tasks = []

    conn.close()
    return tasks
