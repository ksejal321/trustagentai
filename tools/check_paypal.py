"""
Quick PayPal sandbox check. Run from the project folder:   python check_paypal.py
Reads PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET from .streamlit/secrets.toml or the environment.
Never prints your keys.
"""
import os

import requests

try:
    import tomllib  # Python 3.11+
except ImportError:  # pragma: no cover
    tomllib = None


def read_setting(name):
    if tomllib and os.path.exists(".streamlit/secrets.toml"):
        try:
            with open(".streamlit/secrets.toml", "rb") as f:
                val = tomllib.load(f).get(name)
            if val:
                return val
        except Exception as e:  # noqa: BLE001
            print(f"Could not read .streamlit/secrets.toml: {e}")
            print("Tip: every value must be inside straight quotes, e.g.  PAYPAL_CLIENT_ID = \"abc...\"")
    return os.environ.get(name)


client_id = read_setting("PAYPAL_CLIENT_ID")
client_secret = read_setting("PAYPAL_CLIENT_SECRET")
if not client_id or not client_secret:
    raise SystemExit("Missing PAYPAL_CLIENT_ID or PAYPAL_CLIENT_SECRET in .streamlit/secrets.toml")

print("Asking PayPal Sandbox for an access token...")
try:
    r = requests.post(
        "https://api-m.sandbox.paypal.com/v1/oauth2/token",
        auth=(client_id, client_secret),
        data={"grant_type": "client_credentials"},
        headers={"Accept": "application/json"},
        timeout=30,
    )
except Exception as e:  # noqa: BLE001
    raise SystemExit(f"Could not reach PayPal: {type(e).__name__}: {e}")

if r.status_code == 200:
    body = r.json()
    scopes = body.get("scope", "")
    print("SUCCESS: your PayPal sandbox keys work.")
    print("Payouts permission:", "yes" if "payouts" in scopes.lower() else "NOT SHOWN (tick Payouts in your app's Features and try again)")
else:
    print(f"FAILED (HTTP {r.status_code}). Most likely the Client ID or Secret is wrong, or from a Live app instead of Sandbox.")
    print(r.text[:200])
