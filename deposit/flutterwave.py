import os
import requests


FLUTTERWAVE_BASE_URL = "https://api.flutterwave.com/v3"


def _get_secret_key():
    secret_key = os.getenv("FLW_SECRET_KEY")

    if not secret_key:
        raise RuntimeError("FLW_SECRET_KEY is not configured")

    return secret_key


def _headers():
    return {
        "Authorization": f"Bearer {_get_secret_key()}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def create_virtual_account(
    email,
    amount,
    tx_ref,
    firstname=None,
    lastname=None,
    phone_number=None,
    expires=3600,
):
    """
    Create a Flutterwave NGN dynamic virtual account.
    Always try to force account name to ZEBERO.
    """

    if not email:
        raise ValueError("Customer email is required")

    if not tx_ref:
        raise ValueError("Transaction reference is required")

    try:
        amount = int(float(amount))
    except (TypeError, ValueError):
        raise ValueError("Invalid amount")

    if amount <= 0:
        raise ValueError("Amount must be greater than zero")

    # Force name to ZEBERO
    firstname = "ZEBERO"
    lastname = "ZEBERO"

    payload = {
        "email": email,
        "amount": amount,
        "currency": "NGN",
        "tx_ref": tx_ref,
        "is_permanent": False,
        "expires": int(expires),
        "firstname": firstname,
        "lastname": lastname,
        "narration": "ZEBERO",
    }

    if phone_number:
        payload["phonenumber"] = phone_number

    response = requests.post(
        f"{FLUTTERWAVE_BASE_URL}/virtual-account-numbers",
        headers=_headers(),
        json=payload,
        timeout=30,
    )

    try:
        data = response.json()
    except ValueError:
        raise RuntimeError(
            f"Flutterwave returned invalid JSON (HTTP {response.status_code})"
        )

    if response.status_code >= 400:
        message = data.get("message", "Flutterwave request failed")
        raise RuntimeError(message)

    if data.get("status") != "success":
        raise RuntimeError(
            data.get("message", "Unable to create virtual account")
        )

    account = data.get("data") or {}

    return {
        "status": "success",
        "message": data.get("message"),
        "account_number": account.get("account_number"),
        "bank_name": account.get("bank_name"),
        "account_name": "ZEBERO",
        "amount": account.get("amount", amount),
        "tx_ref": account.get("tx_ref", tx_ref),
        "flw_ref": account.get("flw_ref"),
        "order_ref": account.get("order_ref"),
        "expiry_date": account.get("expiry_date"),
        "raw": data,
    }


def create_bank_transfer(tx_ref, amount, email, name=None):
    """
    Compatibility wrapper used by deposit/routes.py.
    Always forces account name to ZEBERO.
    """

    try:
        result = create_virtual_account(
            email=email,
            amount=amount,
            tx_ref=tx_ref,
            firstname="ZEBERO",
            lastname="ZEBERO",
            expires=600,  # 10 minutes
        )
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
        }

    return {
        "status": "success",
        "message": result.get("message"),
        "data": {
            "account_number": result.get("account_number"),
            "bank_name": result.get("bank_name"),
            "account_name": "ZEBERO",
            "flw_ref": result.get("flw_ref"),
            "order_ref": result.get("order_ref"),
            "amount": result.get("amount"),
            "tx_ref": result.get("tx_ref"),
        },
        "meta": {
            "transfer_account": result.get("account_number"),
            "transfer_bank": result.get("bank_name"),
            "transfer_reference": result.get("flw_ref") or result.get("order_ref"),
            "account_name": "ZEBERO",
        },
    }


def verify_transaction(transaction_id):
    """
    Verify a Flutterwave transaction before crediting the user.
    Returns the transaction data dict.
    """

    if not transaction_id:
        raise ValueError("Transaction ID is required")

    response = requests.get(
        f"{FLUTTERWAVE_BASE_URL}/transactions/{transaction_id}/verify",
        headers=_headers(),
        timeout=30,
    )

    try:
        data = response.json()
    except ValueError:
        raise RuntimeError(
            f"Flutterwave returned invalid JSON (HTTP {response.status_code})"
        )

    if response.status_code >= 400:
        raise RuntimeError(
            data.get("message", "Transaction verification failed")
        )

    if data.get("status") != "success":
        raise RuntimeError(
            data.get("message", "Transaction verification failed")
        )

    return data.get("data") or {}


def verify_by_reference(tx_ref):
    """
    Find a transaction by tx_ref and return it.
    """

    if not tx_ref:
        raise ValueError("Transaction reference is required")

    response = requests.get(
        f"{FLUTTERWAVE_BASE_URL}/transactions",
        headers=_headers(),
        params={
            "tx_ref": tx_ref,
            "currency": "NGN",
        },
        timeout=30,
    )

    try:
        data = response.json()
    except ValueError:
        raise RuntimeError(
            f"Flutterwave returned invalid JSON (HTTP {response.status_code})"
        )

    if response.status_code >= 400:
        raise RuntimeError(
            data.get("message", "Unable to query Flutterwave")
        )

    transactions = data.get("data") or []

    if not transactions:
        return None

    return transactions[0]


# =========================================================
# CREATE TRANSFER (payout)
# =========================================================

def create_transfer(
    account_bank,
    account_number,
    amount,
    narration,
    reference,
):
    if not FLW_SECRET_KEY:
        return _error("FLW_SECRET_KEY is missing from .env")

    payload = {
        "account_bank": account_bank,
        "account_number": account_number,
        "amount": float(amount),
        "currency": "NGN",
        "reference": reference,
        "narration": narration,
        "debit_currency": "NGN",
    }

    try:
        response = requests.post(
            f"{BASE_URL}/transfers",
            headers=headers(),
            json=payload,
            timeout=30,
        )
        try:
            return response.json()
        except ValueError:
            return _error("Flutterwave returned invalid JSON.", response)
    except requests.RequestException as e:
        return _error(str(e))

