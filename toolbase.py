"""Internal tool base: dependency-free tools for content placement and emits."""
import json
import os
import subprocess
import sys
import urllib.request
import urllib.error
import urllib.parse

TOOLS = ["fetch", "place", "emit", "replicate", "youtube", "chroma", "redirect",
         "github", "gitlab", "wikipedia", "wikileaks", "piratebay",
         "onion", "reddit", "tiktok", "instagram", "x", "threads", "yandex", "vscode", "cursor", "devin", "trae", "jetbrains"]

BROWSERS = {
    "chrome": ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser",
               "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
               "/Applications/Chromium.app/Contents/MacOS/Chromium"],
    "classic": ["firefox", "safari", "epiphany", "midori",
                "/Applications/Firefox.app/Contents/MacOS/firefox",
                "/Applications/Safari.app/Contents/MacOS/Safari"],
}


def fetch(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "toolbase/1.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            return {"url": url, "status": r.status, "bytes": len(r.read())}
    except urllib.error.HTTPError as e:
        return {"url": url, "status": e.code, "error": "http"}
    except Exception as e:
        return {"url": url, "status": 0, "error": str(e)}


def place(content, slot):
    return {"slot": slot, "content": content, "placed": True}


def emit(items):
    return {"emits": items, "count": len(items)}


def replicate(item, times):
    return [dict(item, copy=i) for i in range(times)]


def youtube(query):
    q = urllib.parse.quote_plus(query)
    return {"tool": "youtube", "query": query,
            "search_url": f"https://www.youtube.com/results?search_query={q}",
            "watch_hint": "open search_url in a viewer"}


def chroma(url, kind="chrome", open_now=False):
    # chroma = chrome browser + classic internet browsers
    candidates = BROWSERS.get(kind, BROWSERS["chrome"])
    opened = None
    for b in candidates:
        if _which(b):
            if open_now:
                try:
                    subprocess.Popen([b, url])
                    opened = b
                    break
                except OSError:
                    continue
            else:
                opened = b
                break
    return {"tool": "chroma", "kind": kind, "url": url,
            "browser": opened or "none-found", "opened": opened is not None,
            "candidates": candidates}


def redirect(url, kind="chrome"):
    # redirect the samples in browser as it should be (non-blocking)
    return chroma(url, kind, open_now=False)


def github(query):
    q = urllib.parse.quote_plus(query)
    return {"tool": "github", "query": query,
            "search_url": f"https://github.com/search?q={q}",
            "api": "https://api.github.com/search/repositories?q=" + q}


def gitlab(query):
    q = urllib.parse.quote_plus(query)
    return {"tool": "gitlab", "query": query,
            "search_url": f"https://gitlab.com/search?search={q}"}


def wikipedia(query):
    q = urllib.parse.quote_plus(query)
    return {"tool": "wikipedia", "query": query,
            "url": f"https://en.wikipedia.org/wiki/{q}",
            "api": f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={q}&format=json"}


def wikileaks(query):
    q = urllib.parse.quote_plus(query)
    return {"tool": "wikileaks", "query": query,
            "search_url": f"https://search.wikileaks.org/?q={q}"}


def piratebay(query):
    q = urllib.parse.quote_plus(query)
    return {"tool": "piratebay", "query": query,
            "search_url": f"https://thepiratebay.org/search.php?q={q}",
            "note": "public index; verify legality of content"}


def onion(query):
    q = urllib.parse.quote_plus(query)
    return {"tool": "onion", "query": query,
            "note": "Tor .onion; requires Tor proxy to resolve",
            "search_url": f"http://xmh57jrknzkhv6y3ls3ubitzfqnkrwxhopf5aygthi7d6rplyvk3noyd.onion/cgi-bin/omega/omega?P={q}"}


def reddit(query):
    q = urllib.parse.quote_plus(query)
    return {"tool": "reddit", "query": query,
            "search_url": f"https://www.reddit.com/search/?q={q}",
            "json": f"https://www.reddit.com/search.json?q={q}"}


def tiktok(query):
    q = urllib.parse.quote_plus(query)
    return {"tool": "tiktok", "query": query,
            "search_url": f"https://www.tiktok.com/search?q={q}"}


def instagram(query):
    q = urllib.parse.quote_plus(query)
    return {"tool": "instagram", "query": query,
            "url": f"https://www.instagram.com/{q}"}


def x(query):
    q = urllib.parse.quote_plus(query)
    return {"tool": "x", "query": query,
            "search_url": f"https://x.com/search?q={q}"}


def threads(query):
    q = urllib.parse.quote_plus(query)
    return {"tool": "threads", "query": query,
            "search_url": f"https://www.threads.net/search?q={q}"}


def yandex(query):
    q = urllib.parse.quote_plus(query)
    return {"tool": "yandex", "query": query,
            "search_url": f"https://yandex.com/search/?text={q}"}


def vscode(path=".", open_now=False):
    # vscode tool: open a path in VS Code
    candidates = ["code", "/Applications/Visual Studio Code.app/Contents/MacOS/code",
                  "code-insiders"]
    opened = None
    for b in candidates:
        if _which(b):
            if open_now:
                try:
                    subprocess.Popen([b, path])
                    opened = b
                    break
                except OSError:
                    continue
            else:
                opened = b
                break
    return {"tool": "vscode", "path": path, "editor": opened or "none-found",
            "opened": opened is not None}


def cursor(path=".", open_now=False):
    # cursor tool: open a path in Cursor
    candidates = ["cursor", "/Applications/Cursor.app/Contents/MacOS/Cursor"]
    opened = None
    for b in candidates:
        if _which(b):
            if open_now:
                try:
                    subprocess.Popen([b, path])
                    opened = b
                    break
                except OSError:
                    continue
            else:
                opened = b
                break
    return {"tool": "cursor", "path": path, "editor": opened or "none-found",
            "opened": opened is not None}


def devin(query):
    # devin tool: web-based AI software engineer (Cognition)
    q = urllib.parse.quote_plus(query)
    return {"tool": "devin", "query": query,
            "app": "https://devin.ai",
            "session_url": f"https://devin.ai/search?q={q}",
            "note": "web app; requires account"}


def trae(path=".", open_now=False):
    # trae tool: open a path in Trae AI IDE
    candidates = ["trae", "/Applications/Trae.app/Contents/MacOS/Trae"]
    opened = None
    for b in candidates:
        if _which(b):
            if open_now:
                try:
                    subprocess.Popen([b, path])
                    opened = b
                    break
                except OSError:
                    continue
            else:
                opened = b
                break
    return {"tool": "trae", "path": path, "editor": opened or "none-found",
            "opened": opened is not None}


JETBRAINS = [
    "idea", "pycharm", "webstorm", "goland", "clion", "rubymine",
    "phpstorm", "rider", "datagrip",
    "/Applications/IntelliJ IDEA.app/Contents/MacOS/idea",
    "/Applications/PyCharm.app/Contents/MacOS/pycharm",
    "/Applications/WebStorm.app/Contents/MacOS/webstorm",
]


def jetbrains(path=".", open_now=False):
    # jetbrains tool: open a path in any JetBrains IDE
    opened = None
    for b in JETBRAINS:
        if _which(b):
            if open_now:
                try:
                    subprocess.Popen([b, path])
                    opened = b
                    break
                except OSError:
                    continue
            else:
                opened = b
                break
    return {"tool": "jetbrains", "path": path, "ide": opened or "none-found",
            "opened": opened is not None, "candidates": JETBRAINS}


def _which(name):
    if os.path.isabs(name):
        return os.path.exists(name)
    for p in os.environ.get("PATH", "").split(os.pathsep):
        if os.path.exists(os.path.join(p, name)):
            return True
    return False


def toolbase():
    return {"tools": TOOLS, "internal": True, "deps": "stdlib-only"}


if __name__ == "__main__":
    print(json.dumps(toolbase(), indent=2))