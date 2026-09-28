import os
import hmac
import base64

from flask import (
    Blueprint,
    request,
    jsonify,
)

from dotenv import load_dotenv

from deposit.flutterwave import (
    verify_transaction,
    verify_by_reference,
)

from deposit.models import (
    get_deposit,
    complete_deposit,
)


load_dotenv()


deposit_webhook_bp = Blueprint(
    "deposit_webhook",
    __name__,
)


def verify_webhook_signature():

    secret_hash = os.getenv(
        "FLW_SECRET_HASH",
        ""
    ).strip()

    if not secret_hash:
        print(
            "ERROR: FLW_SECRET_HASH is missing."
        )
        return False

    # New Flutterwave signature
    signature = request.headers.get(
        "flutterwave-signature"
    )

    if signature:

        raw_body = request.get_data()

        expected = hmac.new(
            secret_hash.encode("utf-8"),
            raw_body,
            "sha256",
        ).digest()

        expected_signature = (
            base64.b64encode(
                expected
            ).decode("utf-8")
        )

        return hmac.compare_digest(
            expected_signature,
            signature,
        )

    # Legacy Flutterwave signature
    old_signature = request.headers.get(
        "verif-hash"
    )

    if old_signature:
        return hmac.compare_digest(
            old_signature,
            secret_hash,
        )

    return False


@deposit_webhook_bp.route(
    "/flutterwave/webhook",
    methods=["POST"],
)
def flutterwave_webhook():

    print("\n====================================")
    print("FLUTTERWAVE WEBHOOK RECEIVED")
    print("====================================")

    if not verify_webhook_signature():

        print(
            "INVALID FLUTTERWAVE WEBHOOK SIGNATURE"
        )

        return jsonify({
            "success": False,
            "message": "Invalid signature.",
        }), 401

    payload = request.get_json(
        silent=True
    ) or {}

    print("WEBHOOK PAYLOAD:")
    print(payload)

    event = str(
        payload.get("event")
        or payload.get("type")
        or ""
    ).lower()

    print(
        f"WEBHOOK EVENT: {event}"
    )

    if event not in (
        "charge.completed",
        "charge.completed.v2",
    ):
        print(
            f"IGNORING EVENT: {event}"
        )

        return jsonify({
            "success": True,
        }), 200

    data = payload.get(
        "data",
        {},
    )

    if not isinstance(data, dict):
        return jsonify({
            "success": True,
        }), 200

    transaction_id = data.get("id")

    tx_ref = (
        data.get("tx_ref")
        or data.get("reference")
    )

    flw_ref = (
        data.get("flw_ref")
        or str(transaction_id or "")
    )

    status = str(
        data.get("status", "")
    ).lower()

    currency = str(
        data.get("currency", "")
    ).upper()

    try:
        amount = float(
            data.get("amount", 0)
        )
    except (TypeError, ValueError):
        amount = 0

    print(f"TX_REF: {tx_ref}")
    print(f"TRANSACTION ID: {transaction_id}")
    print(f"FLW REF: {flw_ref}")
    print(f"STATUS: {status}")
    print(f"AMOUNT: {amount}")
    print(f"CURRENCY: {currency}")

    if not tx_ref:
        print("MISSING TX_REF")
        return jsonify({
            "success": True,
        }), 200

    deposit = get_deposit(tx_ref)

    if not deposit:
        print(
            f"LOCAL DEPOSIT NOT FOUND: {tx_ref}"
        )

        return jsonify({
            "success": True,
        }), 200

    print(
        f"LOCAL STATUS: {deposit['status']}"
    )

    if deposit["status"] == "successful":

        print("DEPOSIT ALREADY SUCCESSFUL")

        return jsonify({
            "success": True,
            "already_completed": True,
        }), 200

    if deposit["status"] != "pending":

        print(
            f"DEPOSIT NOT PENDING: "
            f"{deposit['status']}"
        )

        return jsonify({
            "success": True,
        }), 200

    local_amount = float(
        deposit["amount"]
    )

    if status not in (
        "successful",
        "succeeded",
    ):
        print(
            "WEBHOOK PAYMENT NOT SUCCESSFUL"
        )

        return jsonify({
            "success": True,
        }), 200

    if currency != "NGN":
        print("INVALID CURRENCY")

        return jsonify({
            "success": True,
        }), 200

    if amount < local_amount:
        print("WEBHOOK AMOUNT TOO LOW")

        return jsonify({
            "success": True,
        }), 200

    # Verify transaction with Flutterwave
    verification = None

    if transaction_id:
        print("VERIFYING USING TRANSACTION ID...")
        try:
            verification = verify_transaction(transaction_id)
        except Exception as e:
            print(f"TRANSACTION ID VERIFY FAILED: {e}")
            verification = None

    # Fallback
    if not isinstance(verification, dict):
        print("TRYING VERIFY BY TX_REF...")
        try:
            verification = verify_by_reference(tx_ref)
        except Exception as e:
            print(f"VERIFY BY TX_REF FAILED: {e}")
            verification = None

    print("VERIFICATION:")
    print(verification)

    if not isinstance(verification, dict):
        return jsonify({
            "success": True,
        }), 200

    # verify_transaction and verify_by_reference return the transaction data directly
    verified_data = verification

    verified_status = str(
        verified_data.get(
            "status",
            ""
        )
    ).lower()

    verified_tx_ref = (
        verified_data.get("tx_ref")
        or verified_data.get("reference")
    )

    verified_currency = str(
        verified_data.get(
            "currency",
            ""
        )
    ).upper()

    try:
        verified_amount = float(
            verified_data.get(
                "amount",
                0
            )
        )
    except (TypeError, ValueError):
        verified_amount = 0

    verified_flw_ref = (
        verified_data.get("flw_ref")
        or flw_ref
        or str(
            verified_data.get(
                "id",
                ""
            )
        )
    )

    print(
        f"VERIFIED STATUS: {verified_status}"
    )

    print(
        f"VERIFIED TX_REF: {verified_tx_ref}"
    )

    print(
        f"VERIFIED AMOUNT: {verified_amount}"
    )

    print(
        f"VERIFIED CURRENCY: "
        f"{verified_currency}"
    )

    # Strict verification
    if verified_status not in (
        "successful",
        "succeeded",
    ):
        return jsonify({
            "success": True,
        }), 200

    if verified_tx_ref != tx_ref:
        print("TX_REF MISMATCH")

        return jsonify({
            "success": True,
        }), 200

    if verified_currency != "NGN":
        print("VERIFIED CURRENCY INVALID")

        return jsonify({
            "success": True,
        }), 200

    if verified_amount < local_amount:
        print(
            "VERIFIED AMOUNT TOO LOW"
        )

        return jsonify({
            "success": True,
        }), 200

    # Credit balance atomically
    print(
        "PAYMENT VERIFIED SUCCESSFULLY"
    )

    print(
        "CREDITING USER BALANCE..."
    )

    result = complete_deposit(
        tx_ref=tx_ref,
        flw_ref=verified_flw_ref,
    )

    print("DEPOSIT RESULT:")
    print(result)

    print(
        "===================================="
    )

    return jsonify({
        "success": True,
        "deposit_processed": result.get(
            "success",
            False,
        ),
        "already_completed": result.get(
            "already_completed",
            False,
        ),
    }), 200
