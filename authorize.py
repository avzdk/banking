"""Autorisér adgang til Danske Bank via Enable Banking og gem sessionen i session.json."""

import json
import uuid
import webbrowser
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import eb_client

ASPSP = {"name": "Danske Bank", "country": "DK"}
ACCESS_DAYS = 90
SESSION_FILE = Path("session.json")


class CallbackHandler(BaseHTTPRequestHandler):
    code: str | None = None

    def do_GET(self):
        query = parse_qs(urlparse(self.path).query)
        CallbackHandler.code = query.get("code", [None])[0]
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write("<h2>Tak – du kan lukke dette vindue og gå tilbage til terminalen.</h2>".encode())

    def log_message(self, *args):
        pass


def wait_for_code() -> str:
    parsed = urlparse(eb_client.REDIRECT_URL)
    server = HTTPServer((parsed.hostname, parsed.port), CallbackHandler)
    while CallbackHandler.code is None:
        server.handle_request()
    server.server_close()
    return CallbackHandler.code


def main():
    valid_until = (datetime.now(timezone.utc) + timedelta(days=ACCESS_DAYS)).isoformat()
    auth = eb_client.post(
        "/auth",
        {
            "access": {"valid_until": valid_until},
            "aspsp": ASPSP,
            "state": str(uuid.uuid4()),
            "redirect_url": eb_client.REDIRECT_URL,
            "psu_type": "personal",
        },
    )
    print("Åbn dette link i din browser og log ind med MitID:")
    print(auth["url"])
    webbrowser.open(auth["url"])
    print(f"Venter på svar på {eb_client.REDIRECT_URL} ...")

    code = wait_for_code()
    session = eb_client.post("/sessions", {"code": code})

    SESSION_FILE.write_text(json.dumps(session, indent=2, ensure_ascii=False))
    print(f"\nSession oprettet og gemt i {SESSION_FILE} (gyldig til {session['access']['valid_until']}).")
    print("Konti:")
    for acc in session["accounts"]:
        print(f"  - {acc.get('name') or acc.get('product')}: {acc['account_id'].get('iban')}  ({acc['uid']})")


if __name__ == "__main__":
    main()
