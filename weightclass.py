import json
import os
from pathlib import Path

STORAGE = Path(os.environ.get("GROK_STORAGE", "grok storage"))
LOCALHOST = os.environ.get("LOCALHOST", "http://localhost:11434")


class LocalWeight:
    def __init__(self, name, fmt=None):
        self.name = name
        self.fmt = fmt or self._detect(fmt)
        self.path = STORAGE / self.fmt / (name.replace(":", "_") + ".json")
        self.loaded = False

    def _detect(self, _):
        for f in STORAGE.glob("*/" + self.name.replace(":", "_") + ".json"):
            return f.parent.name
        return "gguf"

    def load(self):
        if not self.path.exists():
            raise FileNotFoundError(f"weight not copied: {self.path}")
        self.meta = json.loads(self.path.read_text())
        self.loaded = True
        return self

    def target(self):
        return {"model": self.name, "endpoint": LOCALHOST, "format": self.fmt,
                "loaded": self.loaded, "meta": self.meta if self.loaded else None}


def load_local(name):
    return LocalWeight(name).load()


if __name__ == "__main__":
    import sys
    w = load_local(sys.argv[1] if len(sys.argv) > 1 else "llama3.2:latest")
    print(json.dumps(w.target(), indent=2))