import json
import os
import urllib.request

from weightclass import load_local
from grokheader import write_header, ingest

LOCALHOST = os.environ.get("LOCALHOST", "http://localhost:11434")

GROK_CATEGORIES = {
    "grok-4.7": "llama3.2:latest", "grok-4.6": "llama3.2:latest",
    "grok-4.5": "llama3.2:latest", "grok-4.3": "llama3.2:latest",
    "grok-4.20": "llama3.2:latest", "grok-4.1": "llama3.2:latest",
    "grok-4": "llama3.2:latest", "grok-3": "llama3.2:latest",
    "grok-1": "llama3.2:latest",
}

CATEGORY_TYPES = {
    "reasoning": ["grok-4.7", "grok-4.5", "grok-4.20-reasoning"],
    "fast": ["grok-4.1", "grok-4-fast", "grok-3-fast"],
    "mini": ["grok-3-mini"],
    "code": ["grok-code-fast-1"],
    "open": ["grok-1"],
}


def resolve(grok_model):
    return GROK_CATEGORIES.get(grok_model, "llama3.2:latest")


def fetch(grok_model, prompt):
    write_header()
    aspect = ingest(grok_model)
    local = aspect["ingest_into"]
    load_local(local)
    body = json.dumps({"model": local, "messages": [{"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request(LOCALHOST + "/v1/chat/completions", data=body,
                                 headers={"Content-Type": "application/json",
                                          "X-Grok-Aspect": aspect["dedup_key"]}, method="POST")
    with urllib.request.urlopen(req) as r:
        data = json.load(r)
    return {"grok_category": grok_model, "aspect": aspect["aspect"],
            "gguf_backend": local, "dedup_key": aspect["dedup_key"],
            "output": data["choices"][0]["message"]["content"]}


if __name__ == "__main__":
    import sys
    print(json.dumps(fetch(sys.argv[1] if len(sys.argv) > 1 else "grok-4",
                           " ".join(sys.argv[2:]) or "Say OK"), indent=2))