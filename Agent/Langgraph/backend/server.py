from __future__ import annotations

import json
import os
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from . import store
from .config import settings
from .service import process_prompt
from .agent_modes import list_modes


BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")


class OtariFlowHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=FRONTEND_DIR, **kwargs)

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(HTTPStatus.NO_CONTENT)
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path in {"/api/health"}:
            return self._write_json({"status": "ok", "version": settings.version})
        if parsed.path == "/api/budget":
            return self._write_json(store.get_budget())
        if parsed.path == "/api/stats":
            return self._write_json({"stats": store.get_stats(), "budget": store.get_budget(), "models": store.get_model_metrics()})
        if parsed.path == "/api/history":
            limit = int(parse_qs(parsed.query).get("limit", ["50"])[0])
            return self._write_json(store.get_recent_requests(limit=limit))
        if parsed.path == "/api/attacks":
            return self._write_json(store.get_recent_attacks())
        if parsed.path == "/api/models":
            models = settings.model_catalog()
            return self._write_json(models)
        if parsed.path == "/api/modes":
            return self._write_json(list_modes())
        if parsed.path == "/api/sessions":
            limit = int(parse_qs(parsed.query).get("limit", ["50"])[0])
            return self._write_json(store.get_sessions(limit=limit))
        if parsed.path == "/api/session/history":
            qs = parse_qs(parsed.query)
            session_id = qs.get("session_id", [""])[0]
            if not session_id:
                self.send_error(HTTPStatus.BAD_REQUEST, "session_id required")
                return
            limit = int(qs.get("limit", ["100"])[0])
            return self._write_json(store.get_session_requests(session_id, limit=limit))
        return super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode("utf-8") if length else "{}"
        payload = json.loads(body or "{}")

        if parsed.path == "/api/prompt":
            prompt = str(payload.get("prompt", "")).strip()
            if not prompt:
                self.send_error(HTTPStatus.BAD_REQUEST, "Prompt cannot be empty")
                return
            result = process_prompt(
                prompt,
                session_id=str(payload.get("session_id", "default")),
                agent_mode=str(payload.get("agent_mode", "general")),
            )
            return self._write_json(result)

        if parsed.path == "/api/budget/reset":
            new_total = float(payload.get("new_total", settings.total_budget))
            return self._write_json(store.reset_budget(new_total))

        self.send_error(HTTPStatus.NOT_FOUND, "Unknown endpoint")

    def _write_json(self, data):
        raw = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


def create_server(host: str = "0.0.0.0", port: int | None = None) -> ThreadingHTTPServer:
    store.init_db()
    # Render injects PORT env var; fall back to settings.backend_port for local dev.
    effective_port = port or int(os.environ.get("PORT", settings.backend_port))
    return ThreadingHTTPServer((host, effective_port), OtariFlowHandler)
