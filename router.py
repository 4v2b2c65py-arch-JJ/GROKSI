import json
import os
import sys
import urllib.request
import urllib.error

from keyrule import get_key, sender_token

CONFIG_FILE = os.environ.get("ROUTER_CONFIG", "/tmp/grok_router.json")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
ENDPOINT_FILE = os.environ.get("ENDPOINT_FILE", "/tmp/grok_proxy_uri")


def save_present():
    cfg = {"ollama": OLLAMA_URL, "endpoint_file": ENDPOINT_FILE}
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)
    return cfg


def resolve_proxy():
    env = os.environ.get("GROK_BASE_URL")
    if env:
        return env
    try:
        with open(ENDPOINT_FILE) as f:
            return json.load(f)["uri"]
    except (FileNotFoundError, KeyError, ValueError):
        return None


def route(model):
    if model.startswith("grok"):
        return "xai", resolve_proxy()
    return "gguf", OLLAMA_URL


def call(base, model, prompt, headers=None):
    body = json.dumps({"model": model, "messages": [{"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request(base + "/v1/chat/completions", data=body,
                                 headers=headers or {}, method="POST")
    with urllib.request.urlopen(req) as r:
        return json.load(r)["choices"][0]["message"]["content"]


def main():
    save_present()
    model = sys.argv[1] if len(sys.argv) > 1 else "grok-4"
    prompt = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else "Say hello."
    kind, base = route(model)
    if base is None:
        sys.exit("ERROR: no proxy URI. Start proxy.mjs first.")
    headers = {}
    if kind == "xai":
        key = get_key()
        headers = {"Authorization": f"Bearer {key}", "X-Sender-Token": sender_token(key)}
    print(f"[{kind}] {base} :: {model}")
    print(call(base, model, prompt, headers))


if __name__ == "__main__":
    main()