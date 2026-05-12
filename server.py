import http.server
import json
import os
from datetime import datetime

PORT = 8000
SUGGESTIONS_FILE = "suggestions.txt"
SHARE_REQUESTS_FILE = "share_requests.txt"
SERVE_DIR = os.path.dirname(os.path.abspath(__file__))

class Handler(http.server.SimpleHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        try:
            data = json.loads(body) if body else {}
        except Exception as e:
            self._respond(400, {"ok": False, "error": "Invalid JSON"})
            return

        if self.path == "/suggest":
            text = data.get("text", "").strip()
            if text:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                entry = f"[{timestamp}]\n{text}\n"
                filepath = os.path.join(SERVE_DIR, SUGGESTIONS_FILE)
                if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
                    entry = "\n---\n\n" + entry
                with open(filepath, "a", encoding="utf-8") as f:
                    f.write(entry)
                self._respond(200, {"ok": True})
            else:
                self._respond(400, {"ok": False, "error": "Empty suggestion"})
        elif self.path == "/clear-suggestions":
            password = data.get("password", "").strip()
            if password != "https://youtube.com/@jijthetuber":
                self._respond(403, {"ok": False, "error": "Forbidden"})
                return
            filepath = os.path.join(SERVE_DIR, SUGGESTIONS_FILE)
            with open(filepath, "w", encoding="utf-8") as f:
                pass
            self._respond(200, {"ok": True})
        elif self.path == "/share-request":
            video = data.get("video", "").strip()
            service = data.get("service", "").strip()
            if video and service:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                entry = f"[{timestamp}] {service} share request: {video}\n"
                filepath = os.path.join(SERVE_DIR, SHARE_REQUESTS_FILE)
                with open(filepath, "a", encoding="utf-8") as f:
                    f.write(entry)
                self._respond(200, {"ok": True})
            else:
                self._respond(400, {"ok": False, "error": "Missing video or service"})
        else:
            self._respond(404, {"ok": False, "error": "Not found"})

    def _respond(self, status, data):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/suggestions":
            filepath = os.path.join(SERVE_DIR, SUGGESTIONS_FILE)
            if not os.path.exists(filepath):
                self._respond(200, {"ok": True, "entries": []})
                return
            with open(filepath, "r", encoding="utf-8") as f:
                raw = f.read().strip()
            entries = []
            if raw:
                parts = [part.strip() for part in raw.split("\n---\n\n") if part.strip()]
                for part in parts:
                    if "\n" in part:
                        first_line, rest = part.split("\n", 1)
                        timestamp = first_line.strip().strip("[]")
                        text = rest.strip()
                    else:
                        timestamp = ""
                        text = part
                    entries.append({"timestamp": timestamp, "text": text})
            self._respond(200, {"ok": True, "entries": entries})
        else:
            super().do_GET()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def log_message(self, format, *args):
        print(f"[{datetime.now().strftime('%H:%M:%S')}]", format % args)

os.chdir(SERVE_DIR)
print(f"╔══════════════════════════════════════╗")
print(f"║   Lunar Sooners · Local Server       ║")
print(f"║   http://localhost:{PORT}/hidden.html  ║")
print(f"║   Suggestions → suggestions.txt      ║")
print(f"╚══════════════════════════════════════╝")
http.server.HTTPServer(("", PORT), Handler).serve_forever()
