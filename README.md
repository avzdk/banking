# Bankposteringer fra Danske Bank

Et lille Python-projekt til manuelt at hente posteringer og saldi fra egne private konti i via [Enable Banking](https://enablebanking.com/).

Data gemmes lokalt som JSON med én fil pr. konto og datoperiode. Projektet bruger kontoinformation (AIS), ikke betalingsinitiering, og kræver hverken hosting eller en permanent server.

## Forudsætninger

- Python 3.14 og [uv](https://docs.astral.sh/uv/getting-started/installation/).
- En konto hos Enable Banking og en produktionsapplikation med adgang til dine egne konti.
- MitID og adgang til de relevante konti i Danske Bank.
- En browser til at godkende bankadgangen.

## Installation

Kør følgende fra projektets rodmappe:

```bash
uv python install 3.14
uv sync --locked
cp .env.example .env
mkdir -p secrets
```

`uv` opretter det virtuelle miljø og installerer afhængighederne fra [uv.lock](./uv.lock). Du behøver ikke aktivere miljøet manuelt.

## Opsætning af Enable Banking

### 1. Registrér din egen applikation

1. Opret en konto på [Enable Banking](https://enablebanking.com/sign-in/).
2. Registrér en applikation i [Control Panel](https://enablebanking.com/cp/applications).
3. Vælg **PRODUCTION** for at tilgå rigtige bankkonti. Sandbox giver kun testdata.
4. Registrér denne redirect-URL præcist:

   ```text
   https://localhost:8787/callback
   ```

   Brug `https://`, da `http://` afvises.

5. Udfyld de øvrige påkrævede oplysninger og vilkår i registreringsformularen.
6. Vælg **Generate in the browser (using SubtleCrypto) and export private key**. Gem den downloadede private nøgle som `secrets/private.pem`.
7. Notér dit **Application ID**.

Alternativt kan du registrere applikationen med et selvgenereret certifikat. Den lokale private nøgle skal i så fald høre til netop dette certifikat.

### 2. Udfyld lokal konfiguration

Ret `.env` med dine egne oplysninger:

```dotenv
EB_APP_ID=dit-application-id
EB_KEY_PATH=secrets/private.pem
EB_REDIRECT_URL=https://localhost:8787/callback
```

Application ID identificerer applikationen; det er ikke en hemmelig API-nøgle. API-kald autentificeres med en JWT, som scriptet signerer med din private RSA-nøgle. Der dannes en ny JWT ved hvert API-kald.

### 3. Aktivér adgang til egne konti

Klik **Activate by linking accounts** på applikationen i Control Panel, vælg Danske Bank, og godkend med MitID.

Enable Banking beskriver denne mulighed som *restricted mode* til blandt andet individuel, ikke-kommerciel brug. Appen kan kun hente data fra de konti, der er linket til den. Se de aktuelle [regler for linking af egne konti](https://enablebanking.com/docs/api/linked-accounts/) og Enable Bankings vilkår.

Kontrollér derefter konfiguration og appstatus:

```bash
uv run eb_client.py
```

Kommandoen skal vise din applikation med status **aktiv**.

## Autorisér bankadgangen

Aktivering i Control Panel opretter ikke en session til scriptet. Kør derfor også:

```bash
uv run authorize.py
```

1. Scriptet viser et autorisationslink og forsøger at åbne det i browseren.
2. Følg bankens godkendelsesflow med MitID.
3. Efter godkendelsen sendes browseren til `https://localhost:8787/callback?code=...`.
4. Browseren kan ikke vise siden, da der ikke kører en lokal HTTPS-server. Det er forventet.
5. Kopiér hele adressen fra browserens adresselinje, og indsæt den i terminalen.

Scriptet opretter en session, gemmer den i `session.json` og viser de tilgængelige konti.

Der anmodes om 180 dages adgang, men den faktiske session kan have kortere gyldighed. Brug udløbstidspunktet i scriptets svar som det gældende. Når adgangen udløber eller tilbagekaldes, skal du køre autorisationen igen.

**Del ikke redirect-adressen med autorisationskoden, og indsæt den ikke i issues eller chat.**

## Hent posteringer

Kør kommandoerne fra projektets rodmappe:

```bash
# Fra 90 dage før dags dato til i dag
uv run fetch_transactions.py

# Fra 30 dage før dags dato til i dag
uv run fetch_transactions.py --days 30

# Fra en bestemt dato til i dag
uv run fetch_transactions.py --from 2026-09-01

# En afgrænset periode
uv run fetch_transactions.py --from 2026-09-01 --to 2026-09-30
```

| Argument | Betydning |
|---|---|
| `--days` | Antal dage, der trækkes fra slutdatoen for at beregne startdatoen. Standard: 90. |
| `--from` | Startdato som `YYYY-MM-DD`. Overstyrer `--days`. |
| `--to` | Slutdato som `YYYY-MM-DD`. Standard: dags dato. |

Begge datogrænser er inklusive. Banken bestemmer, hvor langt tilbage der kan hentes posteringer.

Scriptet henter alle konti fra den gemte session og følger automatisk API'ets paginering. Saldi hentes særskilt og er ikke nødvendigvis historiske saldi pr. den valgte slutdato.

### JSON-output

Filerne gemmes som `data/<IBAN>_<fra>_<til>.json`. Hvis en konto ikke har et IBAN, bruges kontoens Enable Banking-id i filnavnet.

Hver fil indeholder:

| Felt | Indhold |
|---|---|
| `account` | Kontooplysninger fra autorisationen. |
| `balances` | Saldi fra bankens saldokald. |
| `transactions` | Posteringer for den valgte periode. |

Beløb leveres som strenge. Retningen på en postering fremgår af `credit_debit_indicator`: `DBIT` er debet, og `CRDT` er kredit.

**En ny hentning med samme konto og datoperiode overskriver den eksisterende fil.** Hentninger med forskellige perioder gemmes i separate filer. Scriptet sammenlægger eller deduplikerer ikke overlappende eksporter.

Se [datamodellen med Mermaid-klassediagram](./docs/datamodel.md) for felter og relationer.

## Projektstruktur

```text
banking/
├── README.md
├── AGENTS.md
├── pyproject.toml
├── uv.lock
├── .env.example
├── .gitignore
├── eb_client.py              # API-klient og JWT-signering
├── authorize.py              # Manuel autorisation og sessionsoprettelse
├── fetch_transactions.py     # Hentning og JSON-eksport
├── docs/
│   └── datamodel.md
├── .env                      # Lokal konfiguration, ignoreres af Git
├── secrets/                  # Privat nøgle, ignoreres af Git
├── session.json              # Banksession, ignoreres af Git
└── data/                     # Bankeksporter, ignoreres af Git
```

## Sikkerhed og offentliggørelse

- Del eller commit aldrig din private nøgle, din banksession eller dine bankeksporter.
- `.env`, `secrets/`, `session.json` og `data/` er udelukket via [.gitignore](./.gitignore).
- Git-ignorering beskytter ikke filer, der allerede er sporet eller findes i tidligere commits. Kontrollér både staged filer og historik før offentliggørelse.
- Undgå at tvinge ignorerede filer ind med `git add -f`.
- JSON-filer og deres filnavne indeholder personlige konto- og transaktionsoplysninger. Del heller ikke terminaludskrifter ukritisk.
- Brug kun opdigtede bankdata i eksempler og tests.

## Fejlfinding

| Problem | Handling |
|---|---|
| `EB_APP_ID` mangler | Opret `.env` ud fra [.env.example](./.env.example), og udfyld dit Application ID. |
| Nøglefilen findes ikke | Kontrollér `EB_KEY_PATH`, og kør fra projektets rodmappe. |
| API'et afviser appen | Kontrollér Application ID, at den private nøgle tilhører appen, og at appen er aktiveret. |
| `unsupported schema` ved registrering | Brug `https://localhost:8787/callback`, ikke `http://`. |
| Browseren kan ikke åbne callback-siden | Forventet. Kopiér hele redirect-adressen fra adresselinjen til terminalen. |
| `session.json` mangler | Kør `uv run authorize.py` først. |
| Sessionen er udløbet eller ikke længere autoriseret | Kør `uv run authorize.py` igen, og godkend med MitID. |

## Dokumentation

- [Projektplan](./docs/plan.md)
- [Datamodel](./docs/datamodel.md)
- [Enable Banking API-reference](https://enablebanking.com/docs/api/reference/)
- [Aktivering med egne konti](https://enablebanking.com/docs/api/linked-accounts/)
- [Officielle kodeeksempler](https://github.com/enablebanking/enablebanking-api-samples)
