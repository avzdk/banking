"""Hent posteringer for alle konti i session.json og gem dem som JSON i data/."""

import argparse
import json
from datetime import date, timedelta
from pathlib import Path

import eb_client

SESSION_FILE = Path("session.json")
DATA_DIR = Path("data")


def fetch_all(account_uid: str, date_from: date, date_to: date) -> list[dict]:
    transactions: list[dict] = []
    params = {"date_from": date_from.isoformat(), "date_to": date_to.isoformat()}
    while True:
        page = eb_client.get(f"/accounts/{account_uid}/transactions", **params)
        transactions.extend(page["transactions"])
        continuation_key = page.get("continuation_key")
        if not continuation_key:
            return transactions
        params["continuation_key"] = continuation_key


def main():
    parser = argparse.ArgumentParser(description="Hent posteringer fra Danske Bank via Enable Banking.")
    parser.add_argument("--days", type=int, default=90, help="Antal dage tilbage (standard: 90)")
    parser.add_argument("--from", dest="date_from", type=date.fromisoformat, help="Startdato (YYYY-MM-DD), overstyrer --days")
    parser.add_argument("--to", dest="date_to", type=date.fromisoformat, default=date.today(), help="Slutdato (YYYY-MM-DD), standard: i dag")
    args = parser.parse_args()
    date_from = args.date_from or args.date_to - timedelta(days=args.days)

    session = json.loads(SESSION_FILE.read_text())
    status = eb_client.get(f"/sessions/{session['session_id']}")
    if status["status"] != "AUTHORIZED":
        print(f"Sessionen er ikke længere gyldig (status: {status['status']}). Kør 'uv run authorize.py' igen.")
        return

    DATA_DIR.mkdir(exist_ok=True)
    for acc in session["accounts"]:
        iban = acc["account_id"].get("iban") or acc["uid"]
        print(f"Henter posteringer for {iban} ({date_from} – {args.date_to}) ...")
        transactions = fetch_all(acc["uid"], date_from, args.date_to)
        balances = eb_client.get(f"/accounts/{acc['uid']}/balances")["balances"]

        out = DATA_DIR / f"{iban}_{date_from}_{args.date_to}.json"
        out.write_text(
            json.dumps(
                {"account": acc, "balances": balances, "transactions": transactions},
                indent=2,
                ensure_ascii=False,
            )
        )
        print(f"  {len(transactions)} posteringer gemt i {out}")


if __name__ == "__main__":
    main()
