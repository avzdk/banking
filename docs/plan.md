# Plan: Hent posteringer fra private konti via Enable Banking

## 1. Hvordan Enable Banking virker (kort)

Enable Banking er en PSD2-aggregator. Flowet for kontoinformation (AIS) er:

1. Vores script autentificerer sig over for `https://api.enablebanking.com` med en **JWT signeret med vores egen RSA-nøgle** (header `Authorization: Bearer <jwt>`).
2. Scriptet kalder `POST /auth` med bank (ASPSP), land, `redirect_url` og gyldighedsperiode → får en **autorisations-URL**.
3. **Du** åbner URL'en i browseren og logger ind i banken med MitID og godkender adgang.
4. Banken sender dig tilbage til vores `redirect_url` med `?code=...` i query-strengen.
5. Scriptet bytter `code` til en **session** via `POST /sessions` → får `session_id` + liste af konti (`account_id`).
6. Herefter kan scriptet frit kalde `GET /accounts/{account_id}/transactions` (med `date_from`, `date_to`, `continuation_key` til paginering) og `GET /accounts/{account_id}/balances`, indtil sessionen udløber (typisk op til 90–180 dage afhængig af bank).

Vigtigt for privat brug: En produktions-app kan aktiveres **uden kontrakt** ved at "whitelist" dine egne konti ("Activate by linking accounts" i Control Panel). Appen kører så i *restricted mode* og kan kun hente data fra netop de konti, du har linket – hvilket er præcis det, vi skal bruge. Sandbox-miljøet giver kun fiktive data, så vi går direkte efter produktion.

## Beslutninger

- Bank: **Danske Bank** (ASPSP `{"name": "Danske Bank", "country": "DK"}`)
- Output: **JSON** – én fil pr. konto pr. periode i `data/`
- Kørsel: **manuel** (`uv run fetch_transactions.py`)
- Python 3.14, `uv` + `pyproject.toml` (jf. AGENTS.md)

## 2. Komponenter

Ét Python-projekt uden server:

```
banking/
├── AGENTS.md
├── docs/plan.md
├── pyproject.toml + uv.lock            # requests, PyJWT[crypto], python-dotenv
├── .env.example                        # skabelon – kopiér til .env
├── .env                                # EB_APP_ID, EB_KEY_PATH, EB_REDIRECT_URL (ikke i git!)
├── .gitignore                          # .env, secrets/, session.json, data/
├── secrets/private.pem + cert.pem      # RSA-nøgle (hemmelig) + certifikat (uploades)
├── eb_client.py                        # JWT-generering + get()/post(); `uv run eb_client.py` = smoke test
├── authorize.py                        # starter /auth, du indsætter redirect-URL med code, opretter session
├── fetch_transactions.py               # henter posteringer + saldi og gemmer JSON
├── session.json                        # gemt session_id + konti (genereres)
└── data/                               # output: <iban>_<fra>_<til>.json
```

| Komponent | Ansvar |
|---|---|
| `eb_client.py` | Bygger RS256-JWT (`iss=enablebanking.com`, `aud=api.enablebanking.com`, `kid=<app_id>`, 1 times TTL) og udstiller `get()`/`post()`. Kørt direkte kalder den `GET /application` som smoke test. |
| `authorize.py` | Kalder `POST /auth` for Danske Bank med 180 dages adgang (Danske Banks maksimum), åbner URL i browseren, beder dig indsætte den URL du lander på (`https://localhost:8787/callback?code=...`), kalder `POST /sessions`, gemmer `session.json`. |
| `fetch_transactions.py` | Læser `session.json`, tjekker at sessionen stadig er `AUTHORIZED`, henter transaktioner (`--days`, `--from`, `--to`) med paginering via `continuation_key` samt saldi, og skriver én JSON-fil pr. konto i `data/`. |

## 3. Nøgler og hemmeligheder – hvad skal vi bruge, og hvor kommer de fra

| Hvad | Hvor fra | Bruges til |
|---|---|---|
| **RSA privat nøgle** (`secrets/private.pem`) | ✅ Genereret i browseren ved app-registrering (4096 bit) og downloadet | Signere JWT |
| **Certifikat** | ✅ Genereret af Enable Banking sammen med nøglen (vores eget `openssl`-nøglepar ligger ubrugt i `secrets/unused/`) | Registreret på appen |
| **Application ID** (UUID) | ✅ `e614711a-610a-4cff-98f2-cf38872beaef` (app "AvzBank") | `kid` i JWT-headeren |
| **Redirect URL** | `https://localhost:8787/callback` – Enable Banking kræver `https://`; skal registreres på appen | Modtage `code` efter bank-login (browseren kan ikke vise siden, men `code` står i adresselinjen) |
| **Session ID** + **account IDs** | Returneres af `POST /sessions` – gemmes lokalt i `session.json` | Alle efterfølgende datakald |

Der er altså ingen "API-key" at kopiere – autentificeringen er nøglepar + app-id. Den private nøgle må aldrig deles eller committes.

## 4. Det du selv skal gøre (kan en AI ikke)

1. **Opret konto hos Enable Banking**: gå til <https://enablebanking.com/sign-in/>, indtast e-mail, klik på engangs-linket i din mail.
2. **Registrér applikationen** i <https://enablebanking.com/cp/applications>:
   - Environment: **PRODUCTION**
   - Navn + beskrivelse (fx "Personlig kontoudtræk")
   - Upload `cert.pem` (jeg genererer den – du uploader)
   - Redirect URL: `https://localhost:8787/callback` (skal være `https://` – `http://` afvises med "unsupported schema")
   - Produktion kræver også `gdpr_email`, `privacy_url` og `terms_url` – for privat brug kan det være din egen e-mail og en simpel side/URL (fx et GitHub-gist eller GitHub Pages).
   - Notér **Application ID** og læg det i `.env`.
3. **Aktivér appen ved at linke dine egne konti**: Klik "Activate by linking accounts" i Control Panel → vælg din bank → log ind med **MitID** → godkend. Status skifter fra *Inactive* til *Active (restricted)*. Gentag for hver bank, du vil hente fra.
4. **Autorisér adgang via scriptet**: Kør `python authorize.py`, åbn den URL scriptet printer, log ind med MitID igen, godkend samtykke. (Linkingen i punkt 3 giver IKKE en API-session – begge trin er nødvendige.)
5. **Gentag punkt 4 når samtykket udløber** (banken bestemmer, typisk 90–180 dage). Scriptet fortæller dig, når det er nødvendigt.
6. **Opbevar nøglerne sikkert**: `private.pem` og `.env` bliver på din maskine, uden for git.

## 5. Det jeg (AI) kan gøre

- Generere nøglepar og certifikat med `openssl`.
- Sætte projektet op (venv, dependencies, `.gitignore`, `.env.example`).
- Skrive `eb_client.py`, `authorize.py` og `fetch_transactions.py` inkl. paginering og JSON-output.
- Teste autentificeringen mod API'et (`GET /application` returnerer app-info og er en god "smoke test" uden bank-login) så snart du har lagt Application ID i `.env`.
- Verificere end-to-end sammen med dig, når du har gennemført MitID-login.

## 6. Rækkefølge og status

| Trin | Hvem | Handling | Status |
|---|---|---|---|
| 1 | AI | Generér `secrets/private.pem` + `secrets/cert.pem`, opret projekt (uv, Python 3.14) | ✅ |
| 2 | AI | Skriv `eb_client.py`, `authorize.py`, `fetch_transactions.py`; verificér JWT-format mod API | ✅ |
| 3 | Du | Opret EB-konto, registrér PRODUCTION-app med `secrets/cert.pem` og redirect-URL `https://localhost:8787/callback`, notér App ID | ✅ |
| 4 | Du | `cp .env.example .env` og indsæt App ID | ✅ |
| 5 | AI/du | Smoke test: `uv run eb_client.py` skal vise appens navn og status | ✅ (AvzBank, PRODUCTION, inaktiv) |
| 6 | Du | "Activate by linking accounts" med MitID i Control Panel | ✅ |
| 7 | Du | `uv run authorize.py` → log ind med MitID → kopiér adressen du lander på ind i terminalen → `session.json` oprettes | ✅ (session gyldig til 2027-01-31) |
| 8 | Du | `uv run fetch_transactions.py --days 90` → JSON i `data/` | ✅ (7 konti, 487 posteringer) |

## 7. Daglig brug

```bash
uv run fetch_transactions.py              # sidste 90 dage
uv run fetch_transactions.py --days 30    # sidste 30 dage
uv run fetch_transactions.py --from 2026-01-01 --to 2026-03-31
```

Når scriptet melder, at sessionen ikke længere er gyldig, kør `uv run authorize.py` igen.

## Referencer

- Datamodel for JSON-output: [datamodel.md](./datamodel.md)
- API-reference: <https://enablebanking.com/docs/api/reference/>
- Whitelisting af egne konti: <https://enablebanking.com/docs/api/linked-accounts/>
- Kodeeksempler (inkl. Python): <https://github.com/enablebanking/enablebanking-api-samples>
