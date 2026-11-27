import hashlib
import os
import socket

from keyrule import get_key

DEFAULT_SEED_PORT = int(os.environ.get("SEED_PORT", "8080"))
RULE_NAME = os.environ.get("RULE_NAME", "frugal")
EXTERNAL_URL = os.environ.get("XAI_URL", "https://api.x.ai")
CHUNK = int(os.environ.get("CHUNK", "12"))


def bind_seed_port(seed=DEFAULT_SEED_PORT, host="127.0.0.1"):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((host, seed))
    return s


def splice(value, size=CHUNK):
    return [value[i:i + size] for i in range(0, len(value), size)]


def seal_rule(seed=DEFAULT_SEED_PORT, external_url=EXTERNAL_URL, size=CHUNK):
    s = bind_seed_port(seed)
    port = s.getsockname()[1]
    s.close()
    key = get_key()
    return {
        "rule": RULE_NAME,
        "local_port": port,
        "seed": seed,
        "external_url": external_url,
        "key_len": len(key),
        "chunk": size,
        "key_chunks": splice(key, size),
    }


if __name__ == "__main__":
    import json
    print(json.dumps(seal_rule(), indent=2))