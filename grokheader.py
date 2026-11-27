import json
import os
from pathlib import Path

STORAGE = Path(os.environ.get("GROK_STORAGE", "grok storage"))
HEADER = STORAGE / "grok_aspect.json"

ASPECT = {
    "aspect": "grok",
    "ingest_into": "llama3.2:latest",
    "format": "gguf",
    "dedup_key": "grok-aspect-v1",
    "map": {
        "grok-4.7": "llama3.2:latest", "grok-4.6": "llama3.2:latest",
        "grok-4.5": "llama3.2:latest", "grok-4.3": "llama3.2:latest",
        "grok-4.20": "llama3.2:latest", "grok-4.1": "llama3.2:latest",
        "grok-4": "llama3.2:latest", "grok-3": "llama3.2:latest",
        "grok-1": "llama3.2:latest",
    },
}


def write_header():
    STORAGE.mkdir(parents=True, exist_ok=True)
    HEADER.write_text(json.dumps(ASPECT, indent=2))
    return HEADER


def read_header():
    return json.loads(HEADER.read_text())


def ingest(model):
    h = read_header()
    return {"aspect": h["aspect"], "requested": model,
            "ingest_into": h["map"].get(model, h["ingest_into"]),
            "dedup_key": h["dedup_key"]}


if __name__ == "__main__":
    import sys
    p = write_header()
    print("header:", p)
    print(json.dumps(ingest(sys.argv[1] if len(sys.argv) > 1 else "grok-4"), indent=2))