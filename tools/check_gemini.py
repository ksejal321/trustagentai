"""
Quick Gemini health check. Run from the project folder:   python check_gemini.py
Reads GEMINI_API_KEY (and optional GEMINI_MODEL) from .streamlit/secrets.toml or the environment.
Never prints your key.
"""
import os
import time

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
    return os.environ.get(name)


key = read_setting("GEMINI_API_KEY")
model = read_setting("GEMINI_MODEL") or "gemini-3.8-flash"
if not key:
    raise SystemExit("No GEMINI_API_KEY found in .streamlit/secrets.toml or the environment.")

from google import genai
from google.genai import types

client = genai.Client(api_key=key, http_options=types.HttpOptions(timeout=60000))
print(f"Model: {model}")
print("Sending a tiny request...")
start = time.time()
try:
    resp = client.models.generate_content(model=model, contents="Reply with the single word: ready")
    print(f"OK in {time.time() - start:.1f}s -> {resp.text.strip()[:40]}")
except Exception as e:  # noqa: BLE001
    print(f"FAILED after {time.time() - start:.1f}s -> {type(e).__name__}: {str(e)[:300]}")
