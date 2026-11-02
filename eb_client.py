"""Lille klient til Enable Banking API med JWT-autentificering."""

import os
from datetime import datetime, timezone
from pathlib import Path

import jwt
import requests
from dotenv import load_dotenv

API_ORIGIN = "https://api.enablebanking.com"
JWT_TTL_SECONDS = 3600

load_dotenv()

APP_ID = os.environ["EB_APP_ID"]
KEY_PATH = Path(os.environ.get("EB_KEY_PATH", "secrets/private.pem"))
REDIRECT_URL = os.environ.get("EB_REDIRECT_URL", "https://localhost:8787/callback")


def make_jwt() -> str:
    iat = int(datetime.now(timezone.utc).timestamp())
    body = {
        "iss": "enablebanking.com",
        "aud": "api.enablebanking.com",
        "iat": iat,
        "exp": iat + JWT_TTL_SECONDS,
    }
    return jwt.encode(body, KEY_PATH.read_bytes(), algorithm="RS256", headers={"kid": APP_ID})


def _headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {make_jwt()}"}


def get(path: str, **params) -> dict:
    r = requests.get(f"{API_ORIGIN}{path}", params=params or None, headers=_headers())
    r.raise_for_status()
    return r.json()


def post(path: str, body: dict) -> dict:
    r = requests.post(f"{API_ORIGIN}{path}", json=body, headers=_headers())
    r.raise_for_status()
    return r.json()


if __name__ == "__main__":
    app = get("/application")
    print(f"Forbundet som app '{app['name']}' ({app['environment']}), status: {'aktiv' if app['active'] else 'inaktiv'}")
    print(f"Redirect-URL'er: {', '.join(app['redirect_urls'])}")
