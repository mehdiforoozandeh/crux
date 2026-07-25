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
import os, sys, json, socket, shutil, socketserver, webbrowser, http.server, urllib.parse, hashlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import engine

WEBUI = os.path.join(os.path.dirname(os.path.abspath(__file__)), "webui")
DEFAULT_PORT = 8787

# What /file/ is allowed to hand back: an explicit extension -> Content-Type map, so the
# route can never be talked into serving a shell script, a key, or the vault's own config.
# Deterministic on purpose (no mimetypes lookup that varies by platform). The extension set
# is engine.SERVABLE_EXT — declared there so the cockpit knows, before it renders a link,
# which artifacts this route will actually serve.
FILE_TYPES = {
    ".md":   "text/markdown; charset=utf-8",   ".txt":  "text/plain; charset=utf-8",
    ".csv":  "text/csv; charset=utf-8",        ".tsv":  "text/tab-separated-values; charset=utf-8",
    ".json": "application/json",               ".pdf":  "application/pdf",
    ".png":  "image/png",                      ".jpg":  "image/jpeg",
    ".jpeg": "image/jpeg",                     ".gif":  "image/gif",
    ".svg":  "image/svg+xml",                  ".webp": "image/webp",
}
assert set(FILE_TYPES) == set(engine.SERVABLE_EXT), "serve/engine artifact allowlists drifted"

# An SVG is the one type here that is also a DOCUMENT: navigate to one directly and any
# <script> inside it runs in the cockpit's own origin, where /snapshot.json (the whole vault)
# is same-origin readable. A figure can come from anywhere — a paper's supplement, a shared
# vault, a symlinked collaborator directory — so artifacts are served under a CSP that
# forbids script and sandboxes the document into an opaque origin. `<img>` rendering, which
# never executes script anyway, is unaffected.
FILE_CSP = "default-src 'none'; img-src 'self' data:; style-src 'unsafe-inline'; sandbox"


def safe_vault_path(root, rel):
    """Resolve a /file/ request to a real file inside the vault, or None.

    Everything is decided LEXICALLY first — absolute paths, backslashes, drive letters,
    empty/dot segments (which covers `..`, already percent-decoded by the caller), dotfiles,
    and unlisted extensions are all refused before the disk is touched. Only then do we ask
    whether the file exists.

    Symlinks under the vault ARE followed: pointing `results/<hid>/` at the run directory
    in your experiment repo is the documented way to keep artifacts where they are produced.
    That is a deliberate escape hatch the vault owner creates, not one a request can forge.
    """
    if not rel or rel.startswith("/") or "\\" in rel or ":" in rel:
        return None
    parts = rel.split("/")
    if any(p in ("", ".", "..") or p.startswith(".") for p in parts):
        return None
    if os.path.splitext(parts[-1])[1].lower() not in FILE_TYPES:
        return None
    path = os.path.join(root, *parts)
    return path if os.path.isfile(path) else None


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
    (a poll picks up on-disk changes) and /wiki/<slug>.json for lazy wiki page bodies.
    Read-only: only GET, and no route ever writes."""
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=WEBUI, **kw)

    def end_headers(self):
        # The cockpit is a live view, often iterated in place: never let a browser serve a
        # stale webui asset (or snapshot) from cache. One choke point covers every response —
        # static files and /snapshot.json alike — so a plain reload always re-fetches.
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def do_GET(self):
        path = urllib.parse.unquote(self.path.split("?", 1)[0])
        if path == "/snapshot.json":
            return self._snapshot()
        if path.startswith("/wiki/") and path.endswith(".json"):
            return self._wiki(path[len("/wiki/"):-len(".json")])
        if path.startswith("/file/"):
            return self._file(path[len("/file/"):])
        return super().do_GET()

    def _snapshot(self):
        try:
            data = json.dumps(engine.snapshot(self.server.root)).encode("utf-8")
        except Exception as e:
            self.send_error(500, f"snapshot failed: {e}")
            return
        # The UI polls ~1/s; an unchanged vault answers 304 with no body. The validator
        # travels in the ETag header and the client echoes it back itself (If-None-Match),
        # so this works alongside Cache-Control: no-store — no browser cache involved.
        etag = '"%s"' % hashlib.sha256(data).hexdigest()[:32]
        if self.headers.get("If-None-Match") == etag:
            self.send_response(304)
            self.send_header("ETag", etag)
            self.end_headers()
            return
        self._send_json(data, etag)

    def _wiki(self, slug):
        """Lazy wiki page body + backlinks. The slug never touches the filesystem —
        engine.wiki_page_payload matches it against the scan + reserved names only."""
        try:
            payload = engine.wiki_page_payload(self.server.root, slug)
        except Exception as e:
            self.send_error(500, f"wiki page failed: {e}")
            return
        if payload is None:
            self.send_error(404, "no such wiki page")
            return
        self._send_json(json.dumps(payload).encode("utf-8"))

    def _file(self, rel):
        """An evidence artifact: the report a hypothesis links, or a figure inside it.
        Read-only like every other route — and a single 404 for every refusal, so the
        response never tells a caller *why* a path was rejected."""
        full = safe_vault_path(self.server.root, rel)
        if not full:
            self.send_error(404, "no such file")
            return
        try:
            size = os.path.getsize(full)
            f = open(full, "rb")
        except OSError:
            self.send_error(404, "no such file")
            return
        with f:
            self.send_response(200)
            self.send_header("Content-Type", FILE_TYPES[os.path.splitext(full)[1].lower()])
            self.send_header("Content-Length", str(size))
            self.send_header("Content-Security-Policy", FILE_CSP)
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            shutil.copyfileobj(f, self.wfile)   # streamed: a large figure never lands in RAM

    def _send_json(self, data, etag=None):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        if etag:
            self.send_header("ETag", etag)
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass  # quiet by default


class _Server(http.server.ThreadingHTTPServer):
    """ThreadingHTTPServer minus the reverse-DNS lookup.

    The stdlib's `HTTPServer.server_bind` calls `socket.getfqdn(host)` purely to fill in
    `server_name` — which crux never reads. That lookup happens between the bind and the
    banner, so on any machine with slow or absent DNS (a locked-down cluster, an offline
    laptop, a CI runner) the URL you are waiting for is held back by a name resolution
    nobody asked for. Measured: instant on a normal Mac, >30s on GitHub's macOS runners.
    """
    def server_bind(self):
        socketserver.TCPServer.server_bind(self)
        self.server_name, self.server_port = self.server_address[0], self.server_address[1]


def make_server(root, port=None, host="127.0.0.1"):
    """Bind a threading HTTP server on `host`. `port=None` auto-selects from DEFAULT_PORT;
    a pinned busy port raises CruxError. The vault root is stashed on the server for the handler."""
    port = find_free_port(host, DEFAULT_PORT) if port is None else port
    try:
        httpd = _Server((host, port), Handler)
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
