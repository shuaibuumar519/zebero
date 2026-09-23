from flask import render_template

from database import get_conn
from auth.admin_required import admin_required


@admin_required
def admin_users():

    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM users
        ORDER BY id DESC
    """)

    users = cursor.fetchall()
    conn.close()

    return render_template(
        "admin/users.html",
        users=users,
    )
