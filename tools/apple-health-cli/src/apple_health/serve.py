"""Local HTTP receiver for iPhone → Mac health sync."""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable

from apple_health import hae, import_xml, ingest


class IngestServer:
    def __init__(
        self,
        host: str,
        port: int,
        token: str,
        *,
        on_ingest: Callable[[dict[str, Any]], None] | None = None,
    ) -> None:
        self.host = host
        self.port = port
        self.token = token.strip()
        self.on_ingest = on_ingest
        self._httpd: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    def serve_forever(self) -> None:
        handler = _make_handler(self.token, self.on_ingest)
        self._httpd = ThreadingHTTPServer((self.host, self.port), handler)
        self._httpd.serve_forever()

    def start_background(self) -> None:
        self._thread = threading.Thread(target=self.serve_forever, daemon=True)
        self._thread.start()

    def shutdown(self) -> None:
        if self._httpd:
            self._httpd.shutdown()
            self._httpd.server_close()


def _make_handler(
    token: str,
    on_ingest: Callable[[dict[str, Any]], None] | None,
) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt: str, *args: Any) -> None:
            return

        def _auth_ok(self) -> bool:
            if not token:
                return True
            header = self.headers.get("Authorization") or ""
            if header.startswith("Bearer ") and header[7:].strip() == token:
                return True
            for key in ("X-AHP-Token", "X-Api-Key", "api-key"):
                alt = self.headers.get(key) or ""
                if alt.strip() == token:
                    return True
            return False

        def _json(self, code: int, body: dict[str, Any]) -> None:
            raw = json.dumps(body, ensure_ascii=False).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def do_GET(self) -> None:
            base = self.path.split("?", 1)[0].rstrip("/")
            if base in ("/health", "/v1/health"):
                self._json(200, {"ok": True, "service": "ahp-ingest"})
                return
            self._json(404, {"ok": False, "error": "not found"})

        def do_POST(self) -> None:
            if not self._auth_ok():
                self._json(401, {"ok": False, "error": "unauthorized"})
                return
            length = int(self.headers.get("Content-Length") or 0)
            if length <= 0 or length > 64 * 1024 * 1024:
                self._json(400, {"ok": False, "error": "invalid body size"})
                return
            raw = self.rfile.read(length)
            path = self.path.split("?", 1)[0]
            if path.rstrip("/") == "/v1/import-xml":
                self._handle_xml(raw)
                return
            ingest_paths = {
                "/v1/ingest",
                "/ingest",
                "/api/ingest",
                "/api/data",
            }
            if path.rstrip("/") not in ingest_paths:
                self._json(404, {"ok": False, "error": "not found"})
                return
            try:
                doc = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as e:
                self._json(400, {"ok": False, "error": f"invalid json: {e}"})
                return
            if not isinstance(doc, dict):
                self._json(400, {"ok": False, "error": "body must be a JSON object"})
                return
            if hae.is_hae_payload(doc):
                result = hae.ingest_hae(doc)
            else:
                result = ingest.ingest_document(doc)
            if on_ingest:
                on_ingest(result)
            self._json(200, {"ok": True, **result})

        def _handle_xml(self, raw: bytes) -> None:
            tmp = Path("/tmp") / f"ahp-ingest-{id(self)}.xml"
            try:
                tmp.write_bytes(raw)
                result = import_xml.import_export_xml(tmp, force=True)
                self._json(200, {"ok": True, **result})
            except OSError as e:
                self._json(500, {"ok": False, "error": str(e)})
            finally:
                tmp.unlink(missing_ok=True)

    return Handler


def default_token() -> str:
    import os
    import secrets

    env = os.environ.get("AHP_INGEST_TOKEN")
    if env and env.strip():
        return env.strip()
    return secrets.token_urlsafe(24)
