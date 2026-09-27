from flask import (
    Blueprint,
    render_template,
    request,
    session,
    redirect,
    url_for,
    jsonify,
)
from datetime import datetime, timedelta

from deposit.models import (
    create_deposit_table,
    create_deposit,
    save_virtual_account,
    get_deposit,
    expire_deposit_if_needed,
    complete_deposit,
)

from deposit.flutterwave import create_virtual_account

deposit_bp = Blueprint("deposit", __name__)

create_deposit_table()


@deposit_bp.route("/deposit")
def deposit_page():
    if "user" not in session:
        return redirect(url_for("index"))

    return render_template("deposit/index.html", user=session.get("user"))


@deposit_bp.route("/deposit/create", methods=["POST"])
def deposit_create():
    if "user" not in session:
        return redirect(url_for("index"))

    user = session["user"]
    user_id = user["id"]

    try:
        amount = float(request.form.get("amount") or request.json.get("amount") or 0)
    except Exception:
        amount = 0

    if amount < 1000:
        return redirect(url_for("deposit.deposit_page"))

    # local deposit record
    dep = create_deposit(user_id, amount)
    tx_ref = dep["tx_ref"]

    # expiry as datetime, then string once
    expires_at = datetime.now() + timedelta(minutes=10)
    expires_str = expires_at.isoformat()

    email = user.get("email") or "user@zebero.com.ng"
    name = user.get("username") or "ZEBERO User"

    # Flutterwave virtual account
    flw = create_virtual_account(
        amount=amount,
        email=email,
        tx_ref=tx_ref,
        name=name,
    )

    print("FLUTTERWAVE CREATE RESPONSE:", flw)

    if not flw or flw.get("status") != "success":
        return render_template(
            "deposit/failed.html",
            message="Could not create virtual account. Try again.",
        )

    data = flw.get("meta") or flw.get("data") or {}
    account_number = (
        data.get("transfer_account")
        or data.get("account_number")
        or ""
    )
    bank_name = (
        data.get("transfer_bank")
        or data.get("bank_name")
        or "Flutterwave"
    )
    account_name = data.get("account_name") or "ZEBERO"
    flw_ref = data.get("transfer_reference") or data.get("flw_ref")

    save_virtual_account(
        tx_ref=tx_ref,
        account_number=account_number,
        bank_name=bank_name,
        account_name=account_name,
        flw_ref=flw_ref,
    )

    return render_template(
        "deposit/transfer.html",
        amount=amount,
        account_number=account_number,
        bank_name=bank_name,
        account_name=account_name,
        tx_ref=tx_ref,
        expires_at=expires_str,
        user=user,
    )


@deposit_bp.route("/deposit/success")
def deposit_success():
    if "user" not in session:
        return redirect(url_for("index"))
    return render_template("deposit/success.html")


@deposit_bp.route("/deposit/failed")
def deposit_failed():
    if "user" not in session:
        return redirect(url_for("index"))
    return render_template("deposit/failed.html")


@deposit_bp.route("/deposit/webhook", methods=["POST"])
def deposit_webhook():
    payload = request.get_json(silent=True) or {}
    data = payload.get("data") or payload

    tx_ref = (
        data.get("tx_ref")
        or data.get("txRef")
        or data.get("reference")
    )
    status = (data.get("status") or "").lower()
    flw_ref = data.get("flw_ref") or data.get("id")

    if tx_ref and status in ("successful", "success", "completed"):
        complete_deposit(tx_ref, flw_ref=str(flw_ref) if flw_ref else None)

    return jsonify({"status": "ok"}), 200
