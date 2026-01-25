import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse

from generate_dashboard import main as generate_dashboard

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
PUBLIC_DIR = BASE_DIR / "public"
SITE_DIR = BASE_DIR


def _load_list(path: Path) -> list[dict]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, list) else []


def _save_list(path: Path, data: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


class DashboardHandler(BaseHTTPRequestHandler):
    def _send_json(self, payload: dict, status: int = 200) -> None:
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_file(self, path: Path, content_type: str) -> None:
        if not path.exists():
            self.send_error(404)
            return
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _read_body(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if length == 0:
            return {}
        body = self.rfile.read(length).decode("utf-8")
        return json.loads(body)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/data":
            payload = {
                "left": _load_list(DATA_DIR / "left_column.json"),
                "big": _load_list(DATA_DIR / "big_events.json"),
                "right": _load_list(DATA_DIR / "right_column.json"),
            }
            self._send_json(payload)
            return

        if parsed.path in ("/", "/editor", "/editor.html"):
            self._send_file(PUBLIC_DIR / "editor.html", "text/html; charset=utf-8")
            return

        if parsed.path == "/dashboard":
            self._send_file(SITE_DIR / "index.html", "text/html; charset=utf-8")
            return

        if parsed.path == "/dashboard.json":
            self._send_file(SITE_DIR / "dashboard.json", "application/json")
            return

        file_path = (SITE_DIR / parsed.path.lstrip("/")).resolve()
        if SITE_DIR in file_path.parents and file_path.is_file():
            content_type = "text/plain; charset=utf-8"
            if file_path.suffix == ".html":
                content_type = "text/html; charset=utf-8"
            elif file_path.suffix == ".css":
                content_type = "text/css; charset=utf-8"
            elif file_path.suffix == ".json":
                content_type = "application/json"
            elif file_path.suffix == ".svg":
                content_type = "image/svg+xml"
            self._send_file(file_path, content_type)
            return

        file_path = (PUBLIC_DIR / parsed.path.lstrip("/")).resolve()
        if PUBLIC_DIR in file_path.parents and file_path.is_file():
            content_type = "text/plain; charset=utf-8"
            if file_path.suffix == ".html":
                content_type = "text/html; charset=utf-8"
            elif file_path.suffix == ".css":
                content_type = "text/css; charset=utf-8"
            elif file_path.suffix == ".json":
                content_type = "application/json"
            elif file_path.suffix == ".svg":
                content_type = "image/svg+xml"
            self._send_file(file_path, content_type)
            return

        self.send_error(404)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/add":
            payload = self._read_body()
            target = payload.get("target")
            item = payload.get("item")
            if target not in {"left", "right", "big"} or not isinstance(item, dict):
                self._send_json({"ok": False, "error": "Invalid payload"}, status=400)
                return

            if target == "left":
                path = DATA_DIR / "left_column.json"
            elif target == "right":
                path = DATA_DIR / "right_column.json"
            else:
                path = DATA_DIR / "big_events.json"

            data = _load_list(path)
            data.append(item)
            _save_list(path, data)
            generate_dashboard()
            self._send_json({"ok": True})
            return

        if parsed.path == "/api/regenerate":
            generate_dashboard()
            self._send_json({"ok": True})
            return

        self.send_error(404)


def run() -> None:
    PUBLIC_DIR.mkdir(parents=True, exist_ok=True)
    server = HTTPServer(("localhost", 8787), DashboardHandler)
    print("Editor running at http://localhost:8787/editor")
    print("Dashboard preview at http://localhost:8787/dashboard")
    server.serve_forever()


if __name__ == "__main__":
    run()
