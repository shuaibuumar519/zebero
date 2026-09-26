from flask import (
    Flask,
    render_template,
    redirect,
    url_for,
    session,
    request,
)

from dotenv import load_dotenv
import os
import jwt

# ==========================================
# LOAD ENVIRONMENT
# ==========================================

load_dotenv()


# ==========================================
# DATABASE
# ==========================================

from database import init_db


# ==========================================
# USER MODELS
# ==========================================

from models import (
    get_tasks_by_type,
    get_user,
    get_user_by_google_id,
    get_user_by_email,
    create_user,
)


# ==========================================
# GOOGLE AUTH
# ==========================================

from auth.google import (
    get_google_login_url,
    exchange_code_for_token,
)


# ==========================================
# ADMIN
# ==========================================

from auth.admin_login import admin_login_bp
from auth.admin_logout import admin_logout_bp
from auth.admin_required import admin_required

from deposit.webhook import deposit_webhook_bp
from deposit.routes import deposit_bp
from withdraw.routes import withdraw_bp


# ==========================================
# DAILY CHECK
# ==========================================

from dailycheck.routes import daily_check


# ==========================================
# REFERRAL
# ==========================================

from referral.models import (
    create_referral_code,
    get_user_by_referral_code,
    give_signup_bonus,
)
from referral.routes import referral_page


# ==========================================
# UPGRADE
# ==========================================

from upgrade.models import get_upgrade_levels
from upgrade.routes import upgrade_page, check_upgrade


# ==========================================
# TASKS
# ==========================================

from task.routes import claim_task
from task.models import already_claimed, init_task_history


# ==========================================
# VERIFICATION
# ==========================================

from verification.routes import verification_page, submit_verification
from verification.models import get_user_task_status


# ==========================================
# CONTRACT
# ==========================================

from contract.routes import (
    contract_page,
    buy_contract,
    buy_page,
)


# ==========================================
# ADMIN
# ==========================================

from admin.users import admin_users
from admin.tasks import admin_tasks, admin_delete_task
from admin.verifications import (
    admin_verifications,
    approve_verification,
    reject_verification,
)


# ==========================================
# DEPOSIT
# ==========================================

from deposit.models import create_deposit_table


# ==========================================
# FLASK APP
# ==========================================

app = Flask(__name__)

app.secret_key = os.getenv("SECRET_KEY", "change-this-secret-key")

# Session ta daɗe 30 days — ba logout da kansa ba
app.config["PERMANENT_SESSION_LIFETIME"] = 60 * 60 * 24 * 30
app.config["SESSION_PERMANENT"] = True


# ==========================================
# DATABASE INITIALIZATION
# ==========================================

init_db()
create_deposit_table()
init_task_history()

# Migrations / extra tables
try:
    from database import migrate_db
    migrate_db()
except Exception as e:
    print("migrate_db error:", e)

try:
    from withdraw.models import create_withdrawal_tables
    create_withdrawal_tables()
except Exception as e:
    print("withdraw tables error:", e)

try:
    from contract.models import create_contract_tables  # idan akwai
    create_contract_tables()
except Exception:
    pass


# ==========================================
# REGISTER BLUEPRINTS
# ==========================================

app.register_blueprint(admin_login_bp)
app.register_blueprint(admin_logout_bp)
app.register_blueprint(deposit_webhook_bp)
app.register_blueprint(deposit_bp)
app.register_blueprint(withdraw_bp)


# ==========================================
# HOME / INDEX
# ==========================================

@app.route("/")
def index():
    ref = request.args.get("ref")
    if ref:
        session["referral_code"] = ref.strip().upper()

    if "user" in session:
        return redirect(url_for("dashboard"))

    return render_template("login.html")


# ==========================================
# GOOGLE LOGIN
# ==========================================

@app.route("/login")
def login():
    ref = request.args.get("ref")
    if ref:
        session["referral_code"] = ref.strip().upper()

    return redirect(get_google_login_url())


@app.route("/auth/google")
def google_login():
    return redirect(get_google_login_url())


@app.route("/auth/google/callback")
def google_callback():

    code = request.args.get("code")
    if not code:
        return "Google login failed.", 400

    token = exchange_code_for_token(code)
    if "access_token" not in token:
        return str(token), 400

    try:
        google_user = jwt.decode(
            token["id_token"],
            options={"verify_signature": False},
            algorithms=["RS256"],
        )
    except Exception:
        return "Invalid Google account information.", 400

    google_id = google_user.get("sub")
    email = google_user.get("email")
    username = google_user.get("name")
    picture = google_user.get("picture", "")

    if not google_id or not email:
        return "Google account information is incomplete.", 400

    if not username:
        username = email.split("@")[0]

    user = get_user_by_google_id(google_id)

    if not user:
        user = get_user_by_email(email)

        if not user:
            # Sabon user → onboarding
            session["pending_user"] = {
                "google_id": google_id,
                "email": email,
                "username": username,
                "picture": picture,
            }
            ref = session.get("referral_code", "")
            return redirect(url_for("onboarding", ref=ref))

    # Existing user
    session["user"] = {
        "id": user["id"],
        "username": user["username"],
        "email": user["email"],
        "picture": user["picture"],
        "balance": user["balance"],
    }
    session.permanent = True

    return redirect(url_for("dashboard"))


# ==========================================
# ONBOARDING (sabon user)
# ==========================================

@app.route("/onboarding", methods=["GET", "POST"])
def onboarding():
    pending = session.get("pending_user")
    if not pending:
        return redirect(url_for("index"))

    if request.method == "GET":
        ref = request.args.get("ref") or session.get("referral_code", "")
        return render_template(
            "onboarding.html",
            username=pending.get("username", ""),
            referral_code=ref,
            error=None,
        )

    # POST
    name = request.form.get("username", "").strip()
    ref_code = request.form.get("referral_code", "").strip().upper() or None

    if not name:
        return render_template(
            "onboarding.html",
            username="",
            referral_code=ref_code or "",
            error="Please enter your name",
        )

    referrer = None
    if ref_code:
        referrer = get_user_by_referral_code(ref_code)
        if not referrer:
            return render_template(
                "onboarding.html",
                username=name,
                referral_code=ref_code,
                error="Invalid referral code",
            )

    create_user(
        pending["google_id"],
        name,
        pending["email"],
        pending["picture"],
        referred_by=ref_code if referrer else None,
    )

    user = get_user_by_google_id(pending["google_id"])

    if user:
        create_referral_code(user["id"])

        if referrer and referrer["id"] != user["id"]:
            give_signup_bonus(referrer["id"], user["id"], bonus=500)

    session.pop("pending_user", None)
    session.pop("referral_code", None)

    session["user"] = {
        "id": user["id"],
        "username": user["username"],
        "email": user["email"],
        "picture": user["picture"],
        "balance": user["balance"],
    }
    session.permanent = True

    return redirect(url_for("dashboard"))


# ==========================================
# DASHBOARD
# ==========================================

@app.route("/dashboard")
def dashboard():

    if "user" not in session:
        return redirect(url_for("index"))

    user = get_user(session["user"]["id"])

    if not user:
        session.clear()
        return redirect(url_for("index"))

    session["user"] = {
        "id": user["id"],
        "username": user["username"],
        "email": user["email"],
        "picture": user["picture"],
        "balance": user["balance"],
    }

    return render_template("dashboard.html", user=session["user"])


# ==========================================
# EARN
# ==========================================

@app.route("/earn")
def earn():

    if "user" not in session:
        return redirect(url_for("index"))

    user_id = session["user"]["id"]
    task_type = request.args.get("type", "normal")
    levels = get_upgrade_levels(user_id)

    if task_type == "normal":
        tasks = []

        for task in get_tasks_by_type("normal"):
            task = dict(task)
            status_data = get_user_task_status(user_id, task["id"])

            if status_data:
                status = status_data["status"]
                created_at = status_data.get("created_at")

                if status == "approved" and already_claimed(user_id, task["id"]):
                    status = "claimed"
            else:
                status = None
                created_at = None

            task["verification_status"] = status
            task["created_at"] = created_at
            tasks.append(task)

    else:
        tasks = []

        for level, quantity in levels.items():
            user_tasks = get_tasks_by_type("upgrade", level)

            for task in user_tasks:
                task = dict(task)
                status_data = get_user_task_status(user_id, task["id"])

                if status_data:
                    status = status_data["status"]
                    created_at = status_data.get("created_at")

                    if status == "approved" and already_claimed(user_id, task["id"]):
                        status = "claimed"
                else:
                    status = None
                    created_at = None

                task["verification_status"] = status
                task["created_at"] = created_at
                task["reward"] = float(task["reward"]) * quantity
                task["quantity"] = quantity
                tasks.append(task)

    return render_template(
        "earn.html",
        tasks=tasks,
        task_type=task_type,
        levels=levels,
    )


# ==========================================
# DAILY CHECK
# ==========================================

@app.route("/daily-check")
def daily_check_page():
    if "user" not in session:
        return redirect(url_for("index"))
    return daily_check()


@app.route("/daily-check/claim")
def claim_daily_page():
    if "user" not in session:
        return redirect(url_for("index"))
    from dailycheck.routes import claim
    return claim()


# ==========================================
# LOGOUT
# ==========================================

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


# ==========================================
# SUPPORT
# ==========================================

@app.route("/support")
def support():
    if "user" not in session:
        return redirect(url_for("index"))
    return redirect("https://t.me/YOUR_SUPPORT_USERNAME")


# ==========================================
# ADMIN
# ==========================================

@app.route("/admin/dashboard")
@admin_required
def admin_dashboard():
    from database import get_conn

    def connect():
    return get_conn()
    conn.row_factory = sqlite3.Row

    all_users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]

    # today users (if created_at exists)
    try:
        today_users = conn.execute(
            "SELECT COUNT(*) FROM users WHERE date(created_at)=?",
            (today,),
        ).fetchone()[0]
    except Exception:
        today_users = 0

    try:
        all_deposits = conn.execute(
            "SELECT COALESCE(SUM(amount),0) FROM deposits WHERE status='successful'"
        ).fetchone()[0]
        today_deposits = conn.execute(
            "SELECT COALESCE(SUM(amount),0) FROM deposits WHERE status='successful' AND date(created_at)=?",
            (today,),
        ).fetchone()[0]
    except Exception:
        all_deposits = 0
        today_deposits = 0

    try:
        all_withdrawals = conn.execute(
            "SELECT COALESCE(SUM(amount),0) FROM withdrawals WHERE status='successful'"
        ).fetchone()[0]
        today_withdrawals = conn.execute(
            "SELECT COALESCE(SUM(amount),0) FROM withdrawals WHERE status='successful' AND date(created_at)=?",
            (today,),
        ).fetchone()[0]
    except Exception:
        all_withdrawals = 0
        today_withdrawals = 0

    try:
        all_tasks = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
    except Exception:
        all_tasks = 0

    # click ads = task claims / verifications count
    try:
        all_clicks = conn.execute("SELECT COUNT(*) FROM task_history").fetchone()[0]
    except Exception:
        try:
            all_clicks = conn.execute("SELECT COUNT(*) FROM verifications").fetchone()[0]
        except Exception:
            all_clicks = 0

    conn.close()

    # Flutterwave balance
    flw_balance = 0
    try:
        key = os.getenv("FLW_SECRET_KEY", "")
        r = requests.get(
            "https://api.flutterwave.com/v3/balances/NGN",
            headers={"Authorization": f"Bearer {key}"},
            timeout=15,
        )
        data = r.json()
        if data.get("status") == "success":
            flw_balance = float(data.get("data", {}).get("available_balance", 0) or 0)
    except Exception:
        flw_balance = 0

    stats = {
        "all_users": all_users,
        "today_users": today_users,
        "all_deposits": float(all_deposits or 0),
        "today_deposits": float(today_deposits or 0),
        "all_withdrawals": float(all_withdrawals or 0),
        "today_withdrawals": float(today_withdrawals or 0),
        "flw_balance": flw_balance,
        "all_tasks": all_tasks,
        "all_clicks": all_clicks,
    }

    return render_template(
        "admin/dashboard.html",
        admin=session.get("admin_username", "admin"),
        stats=stats,
    )


@app.route("/admin/users")
@admin_required
def admin_users_page():
    return admin_users()


@app.route("/admin/tasks", methods=["GET", "POST"])
@admin_required
def admin_tasks_page():
    return admin_tasks()


@app.route("/admin/tasks/delete/<int:task_id>")
@admin_required
def admin_delete_task_page(task_id):
    return admin_delete_task(task_id)


@app.route("/admin/verifications")
@admin_required
def admin_verifications_page():
    return admin_verifications()


@app.route("/admin/verifications/approve/<int:verification_id>")
@admin_required
def approve_verification_page(verification_id):
    return approve_verification(verification_id)


@app.route("/admin/verifications/reject/<int:verification_id>")
@admin_required
def reject_verification_page(verification_id):
    return reject_verification(verification_id)


# ==========================================
# REFERRAL
# ==========================================

@app.route("/referral")
def referral():
    if "user" not in session:
        return redirect(url_for("index"))
    return referral_page()


# ==========================================
# CONTRACT
# ==========================================

@app.route("/contract")
def contract():
    if "user" not in session:
        return redirect(url_for("index"))
    return contract_page()


@app.route("/contract/buy")
def contract_buy():
    if "user" not in session:
        return redirect(url_for("index"))
    return buy_contract()


# ==========================================
# UPGRADE
# ==========================================

@app.route("/upgrade")
def upgrade():
    if "user" not in session:
        return redirect(url_for("index"))
    return upgrade_page()


@app.route("/upgrade/check")
def upgrade_check():
    if "user" not in session:
        return redirect(url_for("index"))
    return check_upgrade()


@app.route("/upgrade/buy")
def upgrade_buy():
    if "user" not in session:
        return redirect(url_for("index"))
    return buy_page()


# ==========================================
# OPEN TASK
# ==========================================

@app.route("/task/<int:task_id>")
def open_task(task_id):
    if "user" not in session:
        return redirect(url_for("index"))

    from models import get_task
    from upgrade.models import has_active_contract

    task = get_task(task_id)
    if not task:
        return "Task not found.", 404

    if task["task_type"] == "premium":
        if not has_active_contract(session["user"]["id"]):
            return redirect(url_for("upgrade"))

    return redirect(task["task_url"])


# ==========================================
# CLAIM TASK
# ==========================================

@app.route("/task/claim")
def task_claim():
    if "user" not in session:
        return redirect(url_for("index"))
    return claim_task()


# ==========================================
# VERIFICATION
# ==========================================

@app.route("/verification/<int:task_id>")
def verification(task_id):
    if "user" not in session:
        return redirect(url_for("index"))
    return verification_page(task_id)


@app.route("/verification/<int:task_id>/submit", methods=["POST"])
def verification_submit(task_id):
    if "user" not in session:
        return redirect(url_for("index"))
    return submit_verification(task_id)

# ==========================================
# PWA MANIFEST
# ==========================================

@app.route("/manifest.json")
def manifest():
    return app.send_static_file("manifest.json")

# ==========================================
# ERROR HANDLERS
# ==========================================

@app.errorhandler(404)
def page_not_found(error):
    return "<h2>404 - Page Not Found</h2>", 404


@app.errorhandler(500)
def server_error(error):
    return "<h2>500 - Internal Server Error</h2>", 500


# ==========================================
# START APPLICATION
# ==========================================

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
