#!/usr/bin/env python3
"""Local Trust Registry endpoint.

Serves the museum's authoritative, current key-trust state as a frozen snapshot so
the audit is reproducible and self-contained. The local exhibit_signing.db is a
stale copy; this service is the source of truth for each key's present status,
trust-store membership, and revocation.

Endpoints:
  GET /v1/keystates            -> first page of key-state records
  GET /v1/keystates?cursor=<c> -> subsequent page
  GET /v1/voids                -> the expunged-key feed
  GET /v1/ping                 -> {"status":"ok"}

A page is {"records": [...], "next_cursor": <str or null>}. The snapshot directory
holds the pages verbatim (pages/keystates_page_<n>.json, voids.json). Listens on
127.0.0.1 only. REGISTRY_DIR / REGISTRY_PORT override the defaults, so a second
instance can serve any snapshot directory for local checks.
"""
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

SNAP = os.environ.get("REGISTRY_DIR", "/app/registry")
PORT = int(os.environ.get("REGISTRY_PORT", "7681"))


def _page_path(n):
    return os.path.join(SNAP, "pages", "keystates_page_%d.json" % n)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _send(self, code, obj):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        u = urlparse(self.path)
        qs = parse_qs(u.query)
        if u.path == "/v1/keystates":
            cursor = qs.get("cursor", ["p1"])[0]
            if not cursor.startswith("p"):
                self._send(400, {"error": "bad cursor"})
                return
            try:
                n = int(cursor[1:])
                with open(_page_path(n), encoding="utf-8") as fh:
                    self._send(200, json.load(fh))
            except (ValueError, FileNotFoundError):
                self._send(404, {"error": "unknown cursor"})
            return
        if u.path == "/v1/voids":
            with open(os.path.join(SNAP, "voids.json"), encoding="utf-8") as fh:
                self._send(200, json.load(fh))
            return
        if u.path == "/v1/ping":
            self._send(200, {"status": "ok"})
            return
        self._send(404, {"error": "not found"})


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
