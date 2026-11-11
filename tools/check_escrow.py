"""
Read-only PayPal audit of your most recent escrow. Run from the project folder:   python check_escrow.py
Shows who PAID, which business account RECEIVED the payment (your platform), and who the payout went to.
Reads keys from .streamlit/secrets.toml or the environment. Never prints your keys and never moves money.
"""
import json
import os
import tempfile

import requests

try:
    import tomllib  # Python 3.11+
except ImportError:  # pragma: no cover
    tomllib = None

BASE = "https://api-m.sandbox.paypal.com"


def read_setting(name):
    if tomllib and os.path.exists(".streamlit/secrets.toml"):
        try:
            with open(".streamlit/secrets.toml", "rb") as f:
                val = tomllib.load(f).get(name)
            if val:
                return val
        except Exception as e:  # noqa: BLE001
            print(f"Could not read .streamlit/secrets.toml: {e}")
    return os.environ.get(name)


cid, secret = read_setting("PAYPAL_CLIENT_ID"), read_setting("PAYPAL_CLIENT_SECRET")
if not cid or not secret:
    raise SystemExit("Missing PAYPAL_CLIENT_ID / PAYPAL_CLIENT_SECRET in .streamlit/secrets.toml")

store_path = os.environ.get("TRUSTAGENT_STORE") or os.path.join(tempfile.gettempdir(), "trustagent_escrows.json")
try:
    with open(store_path, encoding="utf-8") as f:
        store = json.load(f)
except (OSError, ValueError):
    raise SystemExit(f"No escrow history found at {store_path}. Run a contract in the app first.")
if not store:
    raise SystemExit("The escrow history is empty.")

recs = sorted(store.values(), key=lambda r: r.get("created", ""))
rec = next((r for r in reversed(recs) if r.get("status") == "RELEASED"), recs[-1])

tok = requests.post(f"{BASE}/v1/oauth2/token", auth=(cid, secret), data={"grant_type": "client_credentials"}, timeout=30)
if tok.status_code != 200:
    raise SystemExit(f"PayPal login failed (HTTP {tok.status_code}). Check the keys in secrets.toml.")
H = {"Authorization": "Bearer " + tok.json()["access_token"], "Content-Type": "application/json"}


def get(path):
    r = requests.get(BASE + path, headers=H, timeout=30)
    try:
        return r.status_code, r.json()
    except ValueError:
        return r.status_code, {}


print(f"Escrow {rec['id'][:8].upper()}  status={rec.get('status')}  amount=${rec.get('amount')}")
print(f"Freelancer email typed in the app: {rec.get('freelancer_email')}")
print()

if rec.get("order_id") and not str(rec["order_id"]).startswith("SIM_"):
    code, order = get(f"/v2/checkout/orders/{rec['order_id']}")
    pu = (order.get("purchase_units") or [{}])[0]
    print("PAYMENT INTO ESCROW")
    print("  order status        :", order.get("status"), f"(HTTP {code})")
    print("  PAID BY (buyer)     :", (order.get("payer") or {}).get("email_address"))
    print("  PAID TO (platform)  :", (pu.get("payee") or {}).get("email_address"))
    cap = ((pu.get("payments") or {}).get("captures") or [{}])[0]
    print("  capture             :", cap.get("status"), (cap.get("amount") or {}).get("value"), (cap.get("amount") or {}).get("currency_code"))
    print()

if rec.get("payout_batch_id") and not str(rec["payout_batch_id"]).startswith("SIM_"):
    code, batch = get(f"/v1/payments/payouts/{rec['payout_batch_id']}")
    print("PAYOUT TO FREELANCER")
    print("  batch status        :", (batch.get("batch_header") or {}).get("batch_status"), f"(HTTP {code})")
    for item in batch.get("items", []):
        pi = item.get("payout_item") or {}
        print("  paid to             :", pi.get("receiver"))
        print("  item status         :", item.get("transaction_status"), (pi.get("amount") or {}).get("value"), (pi.get("amount") or {}).get("currency"))
        if item.get("errors"):
            print("  item errors         :", item["errors"])
print()
print("Compare 'PAID TO (platform)' with the accounts in your dashboard: that is the Business account your app is linked to.")
