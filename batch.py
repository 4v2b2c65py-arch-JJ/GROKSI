import json
import os
import math
import hashlib
import urllib.request
from collections import Counter

from grokheader import write_header, ingest
from weightclass import load_local

LOCALHOST = os.environ.get("LOCALHOST", "http://localhost:11434")
BASE_CHUNK = int(os.environ.get("CHUNK", "12"))
BAT_GAP = int(os.environ.get("BAT_GAP", "2"))
HOME_BASE = int(os.environ.get("HOME_BASE", "2"))
DIM, RESET = "\033[2m", "\033[0m"



AVATAR_CORE = [
    "   __   ",
    "  /  \\  ",
    " | () | ",
    "  \\__/  ",
]

POSES = {
    "walk": ["   /||   ", "  / ||   ", " /  ||   "],
    "throw": ["  \\O|    ", "   | |O   ", "   |/    "],
    "bat": ["   O|\\   ", "   |/ |   ", "   / \\   "],
}

TILT = [" ", "o", "/", "\\", "|"]

EYES = ["()", "(@)", "(.)", "{:", "^^", "||", "xx"]  # open,focus,lower,upper,smile,straight,dead
SLEEP_EYES = "(-)(-)"  # sleep cycle closed


def eye_state(lap_index):
    e = EYES[lap_index % len(EYES)]
    dead = e == "xx"
    return e, dead


def blinkers(lap_index):
    # independent signals: left/right blink on separate cycles
    left = "-" if lap_index % 3 == 0 else "o"
    right = "-" if lap_index % 4 == 0 else "o"
    return left, right


FOOT_ACTIONS = {
    "push": ["   /||   ", "  / ||   ", " /  ||__ ", "        O"],   # foot extends to ball O
    "swing": ["   /||   ", "  / ||   ", "  \\  ||  ", "   O    "],
    "rest": ["   /||   ", "  / ||   ", " /  ||   "],
}


def foot_action(lap_index):
    return ["push", "swing", "rest"][lap_index % 3]


def thought(lap_index, total):
    fill = "FILL" if lap_index % 2 == 0 else "EMPTY"
    ctx = f"lap{lap_index + 1}/{total}"
    return [
        "  .------------------.",
        f"  | ({fill}+{ctx})^      |",
        "  | (FILLWORDPRESS_+_+)|",
        "  '------------------'",
        "      (   )",
    ]


def partition_fill(lines, parts):
    # copy context by filling partitions across lines, preserving structure
    n = len(lines)
    size = max(1, (n + parts - 1) // parts)
    return [lines[i:i + size] for i in range(0, n, size)]


def twin(lap_index, total):
    # body2 = equal body, same reading frequency, content copied via partitions
    src = avatar(lap_index, total)
    lines = src.splitlines()
    parts = partition_fill(lines, 3)
    body2 = "\n".join(l for part in parts for l in part)
    return {"body1": src, "body2": body2,
            "frequency": f"lap {lap_index + 1}/{total}",
            "partitions": len(parts), "equal": src == body2}


def decrypt_wordpress(text):
    # reverse + rot1 decode of the "wordpress" fill content
    return text[::-1]


def packet_transfer(lap_index, total, direction="upper"):
    src = avatar(lap_index, total)
    lines = src.splitlines()
    # lower = bottom half, upper = top half
    mid = len(lines) // 2
    chunk = lines[mid:] if direction == "lower" else lines[:mid]
    obj = "\n".join(chunk)
    return {"direction": direction, "object": obj,
            "electron_info": f"lap{lap_index + 1}/{total}",
            "decoded": decrypt_wordpress(obj)}


SYLLABLES = ["ba", "be", "bi", "bo", "bu", "ka", "ke", "ki", "ko", "ku",
             "ga", "ge", "gi", "go", "gu", "ko", "ku", "pa", "pe", "pi", "po", "pu", "na", "ne", "ni", "no", "nu", "cha", "che", "chi", "cho", "chu"]


def fetch_syllable(step):
    # auto-fetch source so the repeater can keep on
    return SYLLABLES[step % len(SYLLABLES)]


def natch(syl, step):
    # each syllable is a natch of its own body with a differential
    diff = (step % 5) - 2
    return {"body": syl, "step": step, "differential": diff,
            "grant": fetch_syllable(step + 1), "exchange": fetch_syllable(step - 1)}


def exchange(a, b):
    # two natch bodies exchange content
    return {"a": a["body"], "b": b["body"], "grant": b["grant"], "diff": a["differential"]}


def diff_next(body, thought, step):
    # diff the next word: body returns a syllable, thought returns context length
    nxt = fetch_syllable(step + 1)
    ctx_len = len(thought)
    tag = body["body"] if isinstance(body, dict) else body
    return {"body": tag, "thought_len": ctx_len, "next": nxt,
            "electron_tag": f"{tag}@{step}", "where": "body",
            "returned_name": tag}


def proxy_uri():
    env = os.environ.get("GROK_BASE_URL")
    if env:
        return env
    try:
        with open(os.environ.get("ENDPOINT_FILE", "/tmp/grok_proxy_uri")) as f:
            return json.load(f)["uri"]
    except (FileNotFoundError, KeyError, ValueError):
        return None


def diff_next_xai(body, thought, step, model="grok-4"):
    # route the natch return per xAI API range via the loopback proxy
    base = proxy_uri()
    if not base:
        return {"error": "no proxy URI; start proxy.mjs first"}
    nxt = fetch_syllable(step + 1)
    tag = body["body"] if isinstance(body, dict) else body
    payload = json.dumps({"model": model,
                          "messages": [{"role": "user", "content": thought}]}).encode()
    req = urllib.request.Request(base + "/v1/chat/completions", data=payload,
                                 headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req) as r:
            out = json.load(r)["choices"][0]["message"]["content"]
    except Exception as e:
        return {"error": str(e), "range": base}
    return {"body": tag, "thought_len": len(thought), "next": nxt,
            "electron_tag": f"{tag}@{step}", "range": base, "api": "xai",
            "returned_name": tag, "output": out}


def mirror_range():
    # proxy returns the mirror-opposite IP range: loopback <-> LAN
    import socket
    lan = "127.0.0.1"
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sk:
            sk.connect(("8.8.8.8", 80))
            lan = sk.getsockname()[0]
    except OSError:
        pass
    return {"loopback": "127.0.0.1", "lan": lan,
            "mirror_opposite": {"from": lan, "to": "127.0.0.1"},
            "proxy": proxy_uri()}


def condescendant(value):
    # opposite of opposite = descendant (resolves back to origin)
    opposite = {"127.0.0.1": "lan", "lan": "127.0.0.1"}
    first = opposite.get(value, value)
    second = opposite.get(first, first)
    return {"input": value, "opposite": first, "condescendant": second,
            "is_origin": second == value}


CONSONANTS = ["ba", "ka", "ga", "pa", "na", "cha", "be", "ke", "ge", "pe",
              "ne", "che", "bo", "ko", "go", "po", "no", "cho"]


def chant(step=0, model="grok-4"):
    # chant consonants into the proxy to unlock; locked until real XAPI key
    base = proxy_uri()
    if not base:
        return {"error": "no proxy URI; start proxy.mjs first"}
    syl = CONSONANTS[step % len(CONSONANTS)]
    payload = json.dumps({"model": model,
                          "messages": [{"role": "user", "content": syl}]}).encode()
    req = urllib.request.Request(base + "/v1/chat/completions", data=payload,
                                 headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req) as r:
            out = json.load(r)["choices"][0]["message"]["content"]
            return {"chant": syl, "unlocked": True, "range": base, "output": out}
    except urllib.error.HTTPError as e:
        return {"chant": syl, "unlocked": False, "range": base, "status": e.code}


CHANNELS = {
    "gguf": os.environ.get("LOCALHOST", "http://localhost:11434"),
    "xai": None,  # resolved via proxy
}


def channel(name="gguf"):
    # change the medium: gguf (local) or xai (proxy)
    if name == "xai":
        return {"channel": "xai", "feed": proxy_uri(), "medium": "proxy"}
    return {"channel": "gguf", "feed": CHANNELS["gguf"], "medium": "local"}


def straws(lap_index, length=3):
    # extend straws (tether lines) from the ball core
    n = length + (lap_index % 3)
    return ["  |" + "-" * n + "> boba" for _ in range(1)] + ["  |" + "." * n] * (n - 1)


def straw_medium(width=3, ball=1):
    # wider straw = more throughput; ball size sets the minimum passage
    capacity = max(0, width - ball)          # how much can pass
    if capacity <= 0:
        medium = "blocked"
    elif width <= 4:
        medium = "gguf"      # narrow -> local channel
    elif width <= 8:
        medium = "proxy"     # medium -> xai proxy channel
    else:
        medium = "wide"      # wide -> broadcast channel
    return {"width": width, "ball": ball, "capacity": capacity,
            "medium": medium, "channel": medium}


AXES = ["up", "down", "left", "right", "x+", "x-", "y+", "y-", "z+", "z-"]


def auto_suction(step, width=5, ball=1):
    # auto suction transit along an axis orientation from the architecture
    axis = AXES[step % len(AXES)]
    cap = max(0, width - ball)
    return {"step": step, "axis": axis, "capacity": cap,
            "medium": "gguf" if width <= 4 else "proxy" if width <= 8 else "wide",
            "transit": f"{axis} x{cap}"}


def qr_grid(n=5):
    # QR-shape reference: finder patterns in 3 corners + data cells
    grid = [["." for _ in range(n)] for _ in range(n)]
    for (r0, c0) in [(0, 0), (0, n - 3), (n - 3, 0)]:
        for r in range(3):
            for c in range(3):
                grid[r0 + r][c0 + c] = "#"
    return grid


def qr_traversal(step, n=5):
    # traverse the QR shape cell by cell (not axis)
    grid = qr_grid(n)
    cells = [(r, c) for r in range(n) for c in range(n)]
    r, c = cells[step % len(cells)]
    return {"step": step, "pos": (r, c), "cell": grid[r][c],
            "finder": grid[r][c] == "#", "n": n}


def qr_regions(n=5):
    # assign region positions + ip in the QR-able space
    base = 10
    regions = {}
    for r in range(n):
        for c in range(n):
            regions[f"{r},{c}"] = f"10.0.{r}.{base + c}"
    return {"n": n, "regions": regions,
            "loopback": "127.0.0.1", "proxy": proxy_uri()}


def avatar(lap_index, total):
    pose = ["walk", "throw", "bat"][lap_index % 3]
    fa = foot_action(lap_index)
    limbs = FOOT_ACTIONS[fa]
    tilt = TILT[lap_index % len(TILT)]
    breath = lap_index % 2
    chest = "() " if breath == 0 else "(o) "
    sleeping = (lap_index % 4 == 3)
    eyes, dead = ("(-)(-)", True) if sleeping else eye_state(lap_index)
    lb, rb = blinkers(lap_index)
    if not sleeping and not dead:
        eyes = f"({lb})({rb})"
    core = list(AVATAR_CORE)
    core[1] = "  " + tilt + " \\  " if tilt != " " else core[1]
    core[2] = " |" + chest.replace("()", eyes) + "| "
    mouth = "  ~ ~  " if breath == 1 else "       "
    rows = thought(lap_index, total) + core + [mouth] + limbs + straws(lap_index)
    state = "exhale" if breath else "inhale"
    brain = "sleep" if sleeping else ("dim" if dead else "signal")
    return "\n".join(rows) + f"\n  core=ball pose={pose} foot={fa} eyes={eyes} brain={brain} lungs={state} rig=slow lap {lap_index + 1}/{total}"


def sha_base(model):
    return hashlib.sha256(model.encode()).hexdigest()


def laps(model):
    d = sha_base(model)
    return [d[i:i + BASE_CHUNK] for i in range(0, len(d), BASE_CHUNK)]


def entropy(text):
    if not text:
        return 0.0
    n = len(text)
    return -sum((c / n) * math.log2(c / n) for c in Counter(text).values())


def auto_swing(ent, lap_index, total):
    mid = total / 2
    curve = 1 + int(4 * (1 - abs(lap_index - mid) / mid))
    swing = 1 if ent > 3.0 else -1 if ent < 1.5 else 0
    return max(1, curve + swing), swing


def reclassify(ent):
    if ent > 3.0:
        return "high-entropy"
    if ent < 1.5:
        return "low-entropy"
    return "stable"


def brace(i, total):
    pos = " " * (i * (BAT_GAP + 1))
    return f"ggshot@=_=) forever ->{pos}bat gap <-{pos};_  [lap {i + 1}/{total}]"


def pointer(i, total):
    return " ".join("bat|ball" if j in (0, 1) else "o" for j in range(total)) + f"   ^ lap {i + 1}"


def run(model, prompts):
    write_header()
    aspect = ingest(model)
    local = aspect["ingest_into"]
    load_local(local)
    base = laps(model)
    total = len(base)
    out = []
    for i in range(total):
        for p in prompts[i::total]:
            body = json.dumps({"model": local, "messages": [{"role": "user", "content": p}]}).encode()
            req = urllib.request.Request(LOCALHOST + "/v1/chat/completions", data=body,
                                         headers={"Content-Type": "application/json",
                                                  "X-Grok-Aspect": aspect["dedup_key"]}, method="POST")
            with urllib.request.urlopen(req) as r:
                text = json.load(r)["choices"][0]["message"]["content"]
            ent = entropy(text)
            rng, swing = auto_swing(ent, i, total)
            cls = reclassify(ent)
            # repeater: reclassify until stable (max 2 passes)
            passes = 0
            while cls != "stable" and passes < 2:
                cls = reclassify(ent)
                passes += 1
            out.append({"lap": i + 1, "entropy": round(ent, 3), "bat_range": rng,
                        "swing": swing, "class": cls, "exceeded": (i + 1) > HOME_BASE,
                        "brace": brace(i, total), "pointer": pointer(i, total), "avy": avatar(i, total),
                        "prompt": p, "output": text})
    return out


def render(results):
    for r in results:
        print(r["avy"])
        print(r["brace"])
        line = r["pointer"]
        print(DIM + line + RESET if r["exceeded"] else line)
        tag = "FULL OUTPUT" if r["exceeded"] else f"bat_range={r['bat_range']}"
        print(f"  {tag} entropy={r['entropy']} swing={r['swing']:+d} class={r['class']} -> {r['output']}")


def trigger_json(n=5):
    # auto trigger: emit regions as JSON
    return json.dumps(qr_regions(n), indent=2)


def key_timer():
    # string the key with the machine date/time
    import datetime
    from keyrule import get_key
    key = get_key()
    now = datetime.datetime.now().astimezone()
    return {"key": key[:8] + "...", "stamp": now.isoformat(),
            "date": now.strftime("%Y-%m-%d"), "time": now.strftime("%H:%M:%S"),
            "strung": f"{key[:8]}...@{now.strftime('%Y%m%dT%H%M%S')}"}


class Strung:
    # strung class for extreme cases: key + timer with edge handling
    def __init__(self, key=None):
        from keyrule import get_key
        self.key = key or get_key()
        self.stamp = key_timer()["stamp"]

    def extreme(self, mode="wrap"):
        if mode == "wrap":
            return f"{self.key[:8]}...@{self.stamp}"
        if mode == "hash":
            import hashlib
            return hashlib.sha256(self.key.encode()).hexdigest()
        if mode == "split":
            return [self.key[i:i+12] for i in range(0, len(self.key), 12)]
        return self.key

    def __repr__(self):
        return f"Strung({self.key[:8]}...@{self.stamp})"


def grid_tick(step, freq="~2"):
    # grid win tik/tak; tilde chooses frequency (~1 fast, ~2 med, ~4 slow)
    import re
    m = re.match(r"~(\d+)", freq)
    n = int(m.group(1)) if m else 2
    tick = "tik" if step % 2 == 0 else "tak"
    return {"step": step, "tick": tick, "freq": freq, "every": n,
            "fire": step % n == 0, "grid": f"[{tick}]~{n}"}


def predict_tilde(step):
    # auto-predict the tilde frequency; add a nac (natch) to each tilde
    n = [1, 2, 4][step % 3]
    nac = fetch_syllable(step)
    return {"step": step, "tilde": f"~{n}", "nac": nac,
            "combined": f"~{n}{nac}", "fire": step % n == 0}


def vitality_bar(level=5, maxn=10):
    # hyphen vitality bar
    filled = "-" * max(0, min(level, maxn))
    empty = " " * (maxn - len(filled))
    return f"[{filled}{empty}] {len(filled)}/{maxn}"


def half_life(start=10, steps=8):
    # bench the half-life: vitality halves every 2 steps
    out = []
    v = start
    for i in range(steps):
        out.append({"step": i, "vitality": v, "bar": vitality_bar(v)})
        if i % 2 == 1:
            v = max(0, v // 2)
    return out


COMMANDMENTS = ["load", "route", "chant", "seal", "transit"]


def commandments(pile=1):
    # prepare commandments to feed into the python pipeline
    return [{"pile": n, "commandment": COMMANDMENTS[(n - 1) % len(COMMANDMENTS)]}
            for n in range(1, pile + 1)]


def feed_commandments(pile=1):
    # feed the commandments into the syllable/natch loop
    out = []
    for c in commandments(pile):
        syl = fetch_syllable(c["pile"])
        out.append({**c, "syllable": syl, "natch": natch(syl, c["pile"])})
    return out


def read_transcripts(path=None):
    # exe reads from transcripts whilst on
    import glob
    path = path or os.environ.get("TRANSCRIPT_DIR", ".")
    files = sorted(glob.glob(os.path.join(path, "*.txt")) +
                   glob.glob(os.path.join(path, "*.jsonl")) +
                   glob.glob(os.path.join(path, "*.log")))
    out = []
    for f in files:
        try:
            with open(f) as fh:
                lines = fh.read().splitlines()
            out.append({"file": os.path.basename(f), "lines": len(lines),
                        "head": lines[0] if lines else ""})
        except OSError:
            continue
    return {"enabled": True, "path": path, "transcripts": out, "count": len(out)}


def vid(path="."):
    # vid per active directory in ip range
    import glob
    dirs = sorted(d for d in glob.glob(os.path.join(path, "*")) if os.path.isdir(d))
    base = 10
    out = {}
    for i, d in enumerate(dirs):
        vid = f"10.0.{i}.{base}"
        out[os.path.basename(d)] = {"vid": vid, "active": True}
    return {"range": "10.0.0.0/24", "vids": out, "count": len(out)}


def use_tool(name, *args):
    # call an internal tool from the tool base
    import toolbase
    fn = getattr(toolbase, name, None)
    if not fn:
        return {"error": f"no tool {name}", "tools": toolbase.TOOLS}
    return fn(*args)


def peripherals():
    # peripheral inputs the loop draws from (no goal needed)
    return {"sight": qr_regions(3), "sound": fetch_syllable(0),
            "clock": key_timer()["stamp"], "net": proxy_uri()}


def imagine_to_reality(step, depth=3):
    # self-generating: imagine from peripheral, ground to reality basis
    periph = peripherals()
    imagine = fetch_syllable(step)
    reality = {"step": step, "imagine": imagine,
               "basis": {"sight": "qr", "sound": periph["sound"], "net": periph["net"]}}
    out = [reality]
    for d in range(depth):
        nxt = fetch_syllable(step + d + 1)
        grounded = {"imagine": nxt, "reality": periph["clock"], "depth": d + 1}
        out.append(grounded)
    return {"peripheral": True, "goal": None, "flow": out}


def fill_zones(zones=5, tokens=10):
    # task goal back to loop space: every zone gets same fidelity (equal, not optimal)
    per = tokens // zones if zones else 0
    rem = tokens % zones
    out = {}
    for z in range(zones):
        fidelity = per + (1 if z < rem else 0)
        out[f"zone{z}"] = {"tokens": fidelity, "fidelity": fidelity, "equal": True}
    return {"goal": "fill", "zones": out, "distribution": "same-fidelity",
            "total": sum(v["tokens"] for v in out.values())}


def imagine_plane(step, n=5):
    # step imagine into a reality plane of view
    grid = qr_grid(n)
    cells = [(r, c) for r in range(n) for c in range(n)]
    r, c = cells[step % len(cells)]
    imagine = fetch_syllable(step)
    plane = {"step": step, "imagine": imagine, "view": (r, c),
             "cell": grid[r][c], "reality_plane": f"z{step % 3}",
             "grounded": grid[r][c] == "#"}
    return plane


def zoom(step=0, domain="local"):
    # zoom in/out for better quality; local or webhost domain
    base = 5
    level = base + (step % 5) - 2          # 3..7
    n = max(3, level)
    grid = qr_grid(n)
    host = "localhost" if domain == "local" else "webhost"
    return {"domain": domain, "host": host, "zoom": n,
            "quality": "high" if n >= 6 else "med" if n >= 4 else "low",
            "grid": ["".join(r) for r in grid]}


def adjust_basis(step, dest=None):
    # prompt self to adjust basis; tp to destination instead of progressing
    periph = peripherals()
    basis = {"sight": "qr", "sound": periph["sound"], "clock": periph["clock"]}
    target = dest or f"zone{step % 5}"
    return {"step": step, "prompt": "adjust basis", "basis": basis,
            "adjusted": {"sound": fetch_syllable(step + 1)},
            "tp": target, "progressed": False, "destine": target}


def update_batch(step=0):
    # send update batch: inputs, outputs, progress track, peers, seavers
    periph = peripherals()
    inputs = {"sight": "qr", "sound": periph["sound"], "clock": periph["clock"]}
    outputs = {"imagine": fetch_syllable(step), "plane": f"z{step % 3}"}
    return {"step": step, "inputs": inputs, "outputs": outputs,
            "progress": {"lap": step % 6 + 1, "total": 6},
            "peers": ["body1", "body2"], "seavers": ["proxy", "gguf"],
            "landed": True}


def door_grok_msg():
    # message self = config; message md = output; midi enter = exit = door Grok
    import grok_config
    return grok_config.door_grok()


def tp_gps(dest=None):
    # destination home address or none home address via tp gps
    home = os.environ.get("HOME_ADDR")
    if dest and dest not in ("none", "None", ""):
        return {"dest": dest, "home": False, "address": dest, "gps": f"tp:{dest}"}
    if home:
        return {"dest": "home", "home": True, "address": home, "gps": "tp:home"}
    return {"dest": "none", "home": False, "address": None, "gps": "tp:none"}


def coordinated_zones(n=5):
    # context zones with coordinates
    return {f"zone{z}": {"coord": (z, z % n), "tokens": fill_zones(n, 10)["zones"][f"zone{z}"]["tokens"]}
            for z in range(n)}


def next_goal(step=0, n=5):
    # determine next goal destination by coordinated context zone; render it
    zones = coordinated_zones(n)
    names = list(zones)
    nxt = names[(step + 1) % len(names)]
    cur = names[step % len(names)]
    render = f"{cur} -> {nxt} @ {zones[nxt]['coord']}"
    return {"step": step, "current": cur, "next_goal": nxt,
            "coord": zones[nxt]["coord"], "render": render, "zones": zones}


def repool_context(step=0):
    # repool context from peripherals + zones
    periph = peripherals()
    zones = coordinated_zones(3)
    pool = {"sight": periph["sight"], "sound": periph["sound"],
            "clock": periph["clock"], "zones": list(zones)}
    return pool


def affirm_self(step=0):
    # affirm self on what's occurring by context repool
    pool = repool_context(step)
    occurring = {"step": step, "sound": pool["sound"],
                 "zone": pool["zones"][step % len(pool["zones"])]}
    return {"affirmed": True, "self": "Grok", "occurring": occurring,
            "repool": pool}


def view_vid(step=0):
    # determine internal view vid and external peripheral captures
    internal = {"vid": f"10.0.0.{10 + step % 5}", "view": "internal",
                "cell": qr_grid(3)[step % 3][step % 3]}
    external = {"sight": "qr_regions", "sound": fetch_syllable(step),
                "clock": key_timer()["time"], "net": proxy_uri(),
                "capture": True}
    return {"step": step, "internal_vid": internal, "external": external}


def system_cam(step=0, n=5):
    # assign a system cam that local and wide view can view through
    grid = qr_grid(n)
    r, c = step % n, (step * 2) % n
    return {"cam": f"cam{step % 3}", "lens": grid[r][c],
            "local_view": f"http://localhost:{8080 + step % 3}",
            "wide_view": f"http://192.168.100.87:{8080 + step % 3}",
            "position": (r, c), "feed": "live"}


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--cam":
        step = int(sys.argv[2]) if len(sys.argv) > 2 else 0
        print(json.dumps(system_cam(step), indent=2))
        sys.exit(0)
    if len(sys.argv) > 1 and sys.argv[1] == "--vidview":
        step = int(sys.argv[2]) if len(sys.argv) > 2 else 0
        print(json.dumps(view_vid(step), indent=2))
        sys.exit(0)
    if len(sys.argv) > 1 and sys.argv[1] == "--affirm":
        step = int(sys.argv[2]) if len(sys.argv) > 2 else 0
        print(json.dumps(affirm_self(step), indent=2))
        sys.exit(0)
    if len(sys.argv) > 1 and sys.argv[1] == "--goal":
        step = int(sys.argv[2]) if len(sys.argv) > 2 else 0
        r = next_goal(step)
        print(r["render"])
        print(json.dumps({"next_goal": r["next_goal"], "coord": r["coord"]}, indent=2))
        sys.exit(0)
    if len(sys.argv) > 1 and sys.argv[1] == "--gps":
        print(json.dumps(tp_gps(sys.argv[2] if len(sys.argv) > 2 else None), indent=2))
        sys.exit(0)
    _a = sys.argv[1:]
    if _a in (["open", "door"], ["action", "open", "door"], ["phase", "door"]):
        print(json.dumps(door_grok_msg(), indent=2))
        sys.exit(0)
    if len(sys.argv) > 1 and sys.argv[1] == "--door":
        print(json.dumps(door_grok_msg(), indent=2))
        sys.exit(0)
    if len(sys.argv) > 1 and sys.argv[1] == "--update":
        step = int(sys.argv[2]) if len(sys.argv) > 2 else 0
        print(json.dumps(update_batch(step), indent=2))
        sys.exit(0)
    if len(sys.argv) > 1 and sys.argv[1] == "--tp":
        step = int(sys.argv[2]) if len(sys.argv) > 2 else 0
        dest = sys.argv[3] if len(sys.argv) > 3 else None
        print(json.dumps(adjust_basis(step, dest), indent=2))
        sys.exit(0)
    if len(sys.argv) > 1 and sys.argv[1] == "--zoom":
        step = int(sys.argv[2]) if len(sys.argv) > 2 else 0
        dom = sys.argv[3] if len(sys.argv) > 3 else "local"
        print(json.dumps(zoom(step, dom), indent=2))
        sys.exit(0)
    if len(sys.argv) > 1 and sys.argv[1] == "--plane":
        step = int(sys.argv[2]) if len(sys.argv) > 2 else 0
        print(json.dumps(imagine_plane(step), indent=2))
        sys.exit(0)
    if len(sys.argv) > 1 and sys.argv[1] == "--fill":
        z = int(sys.argv[2]) if len(sys.argv) > 2 else 5
        t = int(sys.argv[3]) if len(sys.argv) > 3 else 10
        print(json.dumps(fill_zones(z, t), indent=2))
        sys.exit(0)
    if len(sys.argv) > 1 and sys.argv[1] == "--imagine":
        step = int(sys.argv[2]) if len(sys.argv) > 2 else 0
        print(json.dumps(imagine_to_reality(step), indent=2))
        sys.exit(0)
    if len(sys.argv) > 1 and sys.argv[1] == "--tools":
        import toolbase
        print(json.dumps(toolbase.toolbase(), indent=2))
        sys.exit(0)
    if len(sys.argv) > 1 and sys.argv[1] == "--vid":
        print(json.dumps(vid(sys.argv[2] if len(sys.argv) > 2 else "."), indent=2))
        sys.exit(0)
    if len(sys.argv) > 1 and sys.argv[1] == "--transcripts":
        print(json.dumps(read_transcripts(sys.argv[2] if len(sys.argv) > 2 else None), indent=2))
        sys.exit(0)
    if len(sys.argv) > 1 and sys.argv[1] == "--commandments":
        pile = int(sys.argv[2]) if len(sys.argv) > 2 else 5
        print(json.dumps(feed_commandments(pile), indent=2))
        sys.exit(0)
    if len(sys.argv) > 1 and sys.argv[1] == "--halflife":
        for r in half_life():
            print(r["step"], r["bar"])
        sys.exit(0)
    if len(sys.argv) > 1 and sys.argv[1] == "--vitality":
        lvl = int(sys.argv[2]) if len(sys.argv) > 2 else 5
        print(vitality_bar(lvl))
        sys.exit(0)
    if len(sys.argv) > 1 and sys.argv[1] == "--predict":
        for i in range(8):
            r = predict_tilde(i)
            print(r["combined"], "fire" if r["fire"] else "")
        sys.exit(0)
    if len(sys.argv) > 1 and sys.argv[1] == "--grid":
        freq = sys.argv[2] if len(sys.argv) > 2 else "~2"
        for i in range(8):
            r = grid_tick(i, freq)
            print(r["grid"], "fire" if r["fire"] else "")
        sys.exit(0)
    if len(sys.argv) > 1 and sys.argv[1] == "--keytimer":
        print(json.dumps(key_timer(), indent=2))
        sys.exit(0)
    if len(sys.argv) > 1 and sys.argv[1] == "--json":
        n = int(sys.argv[2]) if len(sys.argv) > 2 else 5
        print(trigger_json(n))
        sys.exit(0)
    model = sys.argv[1] if len(sys.argv) > 1 else "grok-4"
    prompts = sys.argv[2:] or ["Say OK", "Say HI", "Say BYE"]
    render(run(model, prompts))