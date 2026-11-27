import hashlib
import os
import secrets
import sys

VENV_DIR = os.environ.get("VIRTUAL_ENV") or os.path.join(os.getcwd(), ".venv")
KEY_FILE = os.path.join(VENV_DIR, ".xapi_key")


def _read():
    try:
        with open(KEY_FILE) as f:
            return f.read().strip()
    except FileNotFoundError:
        return None


def _write(key):
    os.makedirs(VENV_DIR, exist_ok=True)
    with open(KEY_FILE, "w") as f:
        f.write(key)
    os.chmod(KEY_FILE, 0o600)


def generate():
    key = "xai-" + secrets.token_urlsafe(32)
    _write(key)
    return key


def sender_token(key):
    return hashlib.sha256(key.encode()).hexdigest()


def get_key(refresh=None):
    key = os.environ.get("XAPI") or os.environ.get("XAI_API_KEY") or _read()
    if key:
        return key
    if callable(refresh):
        key = refresh()
        if key:
            _write(key)
            return key
    return generate()


if __name__ == "__main__":
    k = get_key()
    print("key_file:", KEY_FILE)
    print("key:", k[:8] + "...")
    print("sender:", sender_token(k))