import json
import os
import sys
import urllib.request
import urllib.error

from keyrule import get_key, sender_token

ENDPOINT_FILE = os.environ.get("ENDPOINT_FILE", "/tmp/grok_proxy_uri")


def resolve_base_url():
    env = os.environ.get("GROK_BASE_URL")
    if env:
        return env
    try:
        with open(ENDPOINT_FILE) as f:
            return json.load(f)["uri"]
    except (FileNotFoundError, KeyError, ValueError):
        sys.exit(f"ERROR: no proxy URI at {ENDPOINT_FILE}. Start proxy.mjs first.")


def refresh():
    return get_key(refresh=None)


api_key = get_key(refresh=refresh)
if not api_key:
    sys.exit("ERROR: no key in env or venv. Run: python3 keyrule.py")

base_url = resolve_base_url()
model = sys.argv[1] if len(sys.argv) > 1 else "grok-4"
prompt = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else "Say hello in one sentence."

body = json.dumps({
    "model": model,
    "messages": [{"role": "user", "content": prompt}],
}).encode()

req = urllib.request.Request(
    base_url + "/v1/chat/completions",
    data=body,
    headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
        "X-Sender-Token": sender_token(api_key),
    },
    method="POST",
)

try:
    with urllib.request.urlopen(req) as r:
        data = json.load(r)
    print(data["choices"][0]["message"]["content"])
except urllib.error.HTTPError as e:
    sys.exit(f"Error {e.code}: {e.read().decode()}")