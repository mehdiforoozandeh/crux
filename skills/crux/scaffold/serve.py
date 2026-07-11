#!/usr/bin/env python3
"""crux serve — a local, read-only browser cockpit over a vault.

Boots Python's stdlib HTTP server bound to 127.0.0.1 on an auto-selected free
port, serves the no-build static frontend in ./webui, and exposes the engine's
`snapshot(vault)` as /snapshot.json (the one machine-readable contract the UI
consumes; the frontend never re-parses markdown). The server performs NO writes —
every mutation stays in the agent/CLI.

Stdlib only. Opening is context-aware (plain terminal / VS Code / Remote-SSH):
localhost binding is exactly what VS Code auto-forwards, and one prominent printed
URL is the universal entry point that never fails.
"""
import os, sys, json, socket, webbrowser, http.server

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import engine

WEBUI = os.path.join(os.path.dirname(os.path.abspath(__file__)), "webui")
DEFAULT_PORT = 8787


# ----------------------------------------------------------------------------- context / opening
def detect_context(env):
    """Return 'remote' | 'vscode' | 'plain' from an env mapping. Pure — no side effects.
    Remote (no display) is the strongest signal, so it wins over a VS Code marker."""
    if env.get("SSH_CONNECTION") or env.get("SSH_TTY") or env.get("SSH_CLIENT"):
        return "remote"
    if env.get("TERM_PROGRAM") == "vscode" or env.get("VSCODE_IPC_HOOK_CLI"):
        return "vscode"
    return "plain"


def local_url(port):
    return f"http://localhost:{port}"


def banner_lines(url, mode):
    """The lines to print on start. Exactly one line carries the clickable URL —
    the universal entry point that linkifies in plain terminals and VS Code alike."""
    lines = ["", f"  crux cockpit (read-only) → {url}", "  Ctrl-C to stop."]
    if mode in ("vscode", "remote"):
        lines.append("  VS Code will offer to open this forwarded port — accept it, "
                     "or Ctrl/Cmd-click the URL → Open in Simple Browser.")
    lines.append("")
    return lines


def maybe_open(url, mode, force_open=None, opener=webbrowser.open):
    """Decide whether to auto-open and, only then, call opener(url). Returns whether it opened.
    Default policy: open the system browser only in a plain local terminal (a remote has no
    display and VS Code forwards the port itself). --open forces, --no-open suppresses."""
    do_open = (mode == "plain") if force_open is None else bool(force_open)
    if do_open:
        try:
            opener(url)
        except Exception:
            pass  # a missing/failed browser must never crash the server
    return do_open


# ----------------------------------------------------------------------------- server
def find_free_port(host, start):
    """First bindable TCP port at or above `start` on `host`."""
    for port in range(start, start + 200):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind((host, port))
                return port
            except OSError:
                continue
    raise engine.CruxError(f"no free port available in {start}..{start + 199}")


class Handler(http.server.SimpleHTTPRequestHandler):
    """Serves the static webui, plus a live /snapshot.json regenerated per request
    (a poll picks up on-disk changes). Read-only: only GET, and no route ever writes."""
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=WEBUI, **kw)

    def end_headers(self):
        # The cockpit is a live view, often iterated in place: never let a browser serve a
        # stale webui asset (or snapshot) from cache. One choke point covers every response —
        # static files and /snapshot.json alike — so a plain reload always re-fetches.
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def do_GET(self):
        if self.path.split("?", 1)[0] == "/snapshot.json":
            return self._snapshot()
        return super().do_GET()

    def _snapshot(self):
        try:
            data = json.dumps(engine.snapshot(self.server.root)).encode("utf-8")
        except Exception as e:
            self.send_error(500, f"snapshot failed: {e}")
            return
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass  # quiet by default


def make_server(root, port=None, host="127.0.0.1"):
    """Bind a threading HTTP server on `host`. `port=None` auto-selects from DEFAULT_PORT;
    a pinned busy port raises CruxError. The vault root is stashed on the server for the handler."""
    port = find_free_port(host, DEFAULT_PORT) if port is None else port
    try:
        httpd = http.server.ThreadingHTTPServer((host, port), Handler)
    except OSError as e:
        raise engine.CruxError(f"cannot bind {host}:{port} — {e}")
    httpd.root = os.path.abspath(root)
    return httpd


def serve(root, port=None, force_open=None, env=None, opener=webbrowser.open):
    """Blocking: start the cockpit host, print the URL banner, maybe open a browser, serve."""
    env = os.environ if env is None else env
    httpd = make_server(root, port=port)
    url = local_url(httpd.server_address[1])
    mode = detect_context(env)
    for line in banner_lines(url, mode):
        print(line)
    sys.stdout.flush()   # the URL must appear immediately, even when stdout is a pipe (block-buffered)
    maybe_open(url, mode, force_open=force_open, opener=opener)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\ncrux: cockpit stopped.")
    finally:
        httpd.server_close()
