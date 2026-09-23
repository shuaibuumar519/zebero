from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    session,
)

from database import get_conn

admin_login_bp = Blueprint("admin_login", __name__)


@admin_login_bp.route("/admin/login", methods=["GET", "POST"])
def admin_login():

    if session.get("admin_logged_in"):
        return redirect(url_for("admin_dashboard"))

    error = None

    if request.method == "POST":

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        conn = get_conn()
        cur = conn.cursor()

        cur.execute(
            """
            SELECT * FROM admins
            WHERE username = ?
            AND password = ?
            """,
            (username, password),
        )

        admin = cur.fetchone()
        conn.close()

        if admin:
            # SQLite Row: admin["id"] ; tuple: admin[0]
            try:
                admin_id = admin["id"]
                admin_username = admin["username"]
            except (TypeError, KeyError):
                admin_id = admin[0]
                admin_username = admin[1]

            session["admin_logged_in"] = True
            session["admin_id"] = admin_id
            session["admin_username"] = admin_username

            return redirect(url_for("admin_dashboard"))

        error = "Invalid username or password."

    return render_template(
        "admin/login.html",
        error=error,
    )
