GROK_MODELS = [
    {"model": "grok-4.7", "version": "4.7", "weights": "closed", "released": "2026-09-21",
     "config": {"context": 500000, "params": None, "layers": None, "experts": None, "hidden": None}},
    {"model": "grok-4.6", "version": "4.6", "weights": "closed", "released": "2026-08-12",
     "config": {"context": 500000, "params": None, "layers": None, "experts": None, "hidden": None}},
    {"model": "grok-4.5", "version": "4.5", "weights": "closed", "released": "2026-08",
     "config": {"context": 500000, "params": None, "layers": None, "experts": None, "hidden": None}},
    {"model": "grok-4.3", "version": "4.3", "weights": "closed", "released": "2026",
     "config": {"context": 1000000, "params": None, "layers": None, "experts": None, "hidden": None}},
    {"model": "grok-4.20", "version": "4.20", "weights": "closed", "released": "2026-03",
     "config": {"context": 1000000, "params": None, "layers": None, "experts": None, "hidden": None}},
    {"model": "grok-4.1", "version": "4.1", "weights": "closed", "released": "2026",
     "config": {"context": 2000000, "params": None, "layers": None, "experts": None, "hidden": None}},
    {"model": "grok-4", "version": "4", "weights": "closed", "released": "2025-07-09",
     "config": {"context": 256000, "params": None, "layers": None, "experts": None, "hidden": None}},
    {"model": "grok-3", "version": "3", "weights": "closed", "released": "2025-02",
     "config": {"context": 131072, "params": None, "layers": None, "experts": None, "hidden": None}},
    {"model": "grok-1", "version": "1", "weights": "open (Apache-2.0)", "released": "2024-03",
     "config": {"context": 8192, "params": "314B", "layers": 64, "experts": 8,
                "hidden": 6144, "heads": 48, "kv_heads": 8, "vocab": 131072}},
]

OPEN_WEIGHTS = [m for m in GROK_MODELS if m["weights"].startswith("open")]

CLOSED_TO_OPEN = {f"grok\\{m['version']}": "grok-1" for m in GROK_MODELS}
CLOSED_TO_OPEN["grok\\moe"] = "grok-1"


def open_case(closed_model):
    return CLOSED_TO_OPEN.get(f"grok\\{closed_model}", "grok-1")


def resolve_all_open(target=None):
    om = GROK_MODELS[-1] if target is None else GROK_MODELS[target]
    return [{"index": i, "source": m["model"],
             "open": om["model"] if m["weights"].startswith("closed") else m["model"]}
            for i, m in enumerate(GROK_MODELS)]


def slider(pos=1, delta=0):
    return (pos + delta) % len(GROK_MODELS), GROK_MODELS[(pos + delta) % len(GROK_MODELS)]["model"]


def branches(pos):
    return {"model": GROK_MODELS[pos]["model"], "config": GROK_MODELS[pos]["config"]}


def entry_condition(model_name):
    m = next((x for x in GROK_MODELS if x["model"] == model_name), None)
    if not m:
        return None
    known = [k for k, v in m["config"].items() if v is not None]
    unknown = [k for k, v in m["config"].items() if v is None]
    return {"model": model_name, "known": known, "unknown": unknown,
            "adjustable": known, "locked": unknown}


def auto_config(model_name, **adjust):
    cond = entry_condition(model_name)
    if not cond:
        return None
    m = next(x for x in GROK_MODELS if x["model"] == model_name)
    for k in cond["adjustable"]:
        if k in adjust:
            m["config"][k] = adjust[k]
    return {"model": model_name, "config": m["config"], "locked": cond["locked"]}


if __name__ == "__main__":
    import json
    for m in GROK_MODELS:
        print(json.dumps(entry_condition(m["model"])))
    print(json.dumps(auto_config("grok-1", context=16384)))