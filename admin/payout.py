from flask import Blueprint, render_template, request, session
from auth.admin_required import admin_required
try:
    from deposit.flutterwave import create_transfer, get_banks
except ImportError:
    from deposit.flutterwave import create_transfer
    def get_banks():
        return {"status": "error", "data": []}
import uuid

admin_payout_bp = Blueprint("admin_payout", __name__)


@admin_payout_bp.route("/admin/payout", methods=["GET", "POST"])
@admin_required
def admin_payout():
    message = None
    error = None

    if request.method == "POST":
        amount = request.form.get("amount", "").strip()
        account_bank = request.form.get("account_bank", "").strip()
        account_number = request.form.get("account_number", "").strip()
        narration = request.form.get("narration", "ZEBERO Admin Payout").strip()

        try:
            amount_f = float(amount)
        except Exception:
            amount_f = 0

        if amount_f < 100:
            error = "Minimum payout is ₦100"
        elif not account_bank or not account_number:
            error = "Bank and account number required"
        else:
            ref = "ADMIN-PAYOUT-" + uuid.uuid4().hex[:12].upper()
            result = create_transfer(
                account_bank=account_bank,
                account_number=account_number,
                amount=amount_f,
                narration=narration or "ZEBERO Admin Payout",
                reference=ref,
            )
            print("ADMIN PAYOUT RESULT:", result)

            if result and result.get("status") == "success":
                message = "Payout initiated. Ref: " + ref
            else:
                err_msg = None
                if isinstance(result, dict):
                    err_msg = result.get("message")
                    if not err_msg and result.get("response"):
                        err_msg = str(result.get("response"))
                error = err_msg or "Payout failed. Is Flutterwave payout enabled?"

    banks = []
    try:
        b = get_banks()
        if b and b.get("status") == "success":
            banks = b.get("data") or []
    except Exception as e:
        print("get_banks error:", e)

    return render_template(
        "admin/payout.html",
        message=message,
        error=error,
        banks=banks,
        admin=session.get("admin_username"),
    )
