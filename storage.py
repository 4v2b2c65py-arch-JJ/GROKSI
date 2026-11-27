import json
import os
import sys
import urllib.request
import urllib.error
import zipfile
from pathlib import Path

from grok_models import GROK_MODELS

SERVER = os.environ.get("OLLAMA_URL", "http://localhost:11434")
STORAGE = Path(os.environ.get("GROK_STORAGE", "grok storage"))
INDEX = STORAGE / "index.zip"


def _get(path):
    with urllib.request.urlopen(SERVER + path) as r:
        return json.load(r)


def list_models():
    return _get("/api/tags")["models"]


def pull(name):
    req = urllib.request.Request(
        SERVER + "/api/pull",
        data=json.dumps({"name": name, "stream": False}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as r:
        return json.load(r)


def partition(model):
    fmt = model.get("details", {}).get("format", "unknown")
    folder = STORAGE / fmt
    folder.mkdir(parents=True, exist_ok=True)
    meta = STORAGE / fmt / (model["name"].replace(":", "_") + ".json")
    meta.write_text(json.dumps(model, indent=2))
    return fmt, meta


def build_index():
    files = sorted(p for p in STORAGE.rglob("*") if p.is_file() and p != INDEX)
    with zipfile.ZipFile(INDEX, "w", zipfile.ZIP_DEFLATED) as z:
        for p in files:
            z.write(p, p.relative_to(STORAGE))
    return INDEX, len(files)


def main():
    models = list_models()
    print(f"Live connection: {SERVER} ({len(models)} models)")
    for m in models:
        fmt, meta = partition(m)
        print(f"  {m['name']} -> {fmt}/")
    (STORAGE / "grok_models.json").write_text(json.dumps(GROK_MODELS, indent=2))
    print(f"Grok catalog: {len(GROK_MODELS)} versions -> grok_models.json")
    idx, n = build_index()
    print(f"Index: {idx} ({n} files)")


if __name__ == "__main__":
    main()