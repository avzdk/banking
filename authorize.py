"""Autorisér adgang til Danske Bank via Enable Banking og gem sessionen i session.json."""

import json
import uuid
import webbrowser
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import eb_client

ASPSP = {"name": "Danske Bank", "country": "DK"}
ACCESS_DAYS = 180
SESSION_FILE = Path("session.json")


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
    print(f"\nNår du er færdig, sendes du til {eb_client.REDIRECT_URL} – siden kan ikke vises, det er forventet.")
    redirected_url = input("Kopiér hele adressen fra browserens adresselinje og indsæt den her: ").strip()

    code = parse_qs(urlparse(redirected_url).query)["code"][0]
    session = eb_client.post("/sessions", {"code": code})

    SESSION_FILE.write_text(json.dumps(session, indent=2, ensure_ascii=False))
    print(f"\nSession oprettet og gemt i {SESSION_FILE} (gyldig til {session['access']['valid_until']}).")
    print("Konti:")
    for acc in session["accounts"]:
        print(f"  - {acc.get('name') or acc.get('product')}: {acc['account_id'].get('iban')}  ({acc['uid']})")


if __name__ == "__main__":
    main()
