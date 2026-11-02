# Datamodel for JSON-filerne i `data/`

Hver fil `data/<IBAN>_<fra>_<til>.json` indeholder ét `AccountExport`-objekt med kontoen, dens saldi og posteringer for perioden. Modellen er udledt af de faktiske data fra Danske Bank via Enable Banking (ISO 20022-inspirerede feltnavne).

```mermaid
classDiagram
    direction LR

    class AccountExport {
        +Account account
        +Balance[] balances
        +Transaction[] transactions
    }

    class Account {
        +string uid  «Enable Banking konto-id, bruges i API-kald»
        +string name
        +string details
        +string usage  «PRIV»
        +string cash_account_type  «CACC | CARD»
        +string currency  «DKK»
        +string identification_hash
        +string[] identification_hashes
        +string? product
        +string? account_servicer
        +string? psu_status
        +Amount? credit_limit
        +string? legal_age
        +PostalAddress? postal_address
    }

    class AccountIdentification {
        +string iban
        +GenericIdentification other
    }

    class GenericIdentification {
        +string identification
        +string scheme_name  «IBAN | BBAN | BANK | CPAN»
        +string? issuer
    }

    class Balance {
        +string name
        +Amount balance_amount
        +string balance_type  «ITAV = disponibel, ITBD = bogført»
        +string reference_date
        +string? last_change_date_time
        +string? last_committed_transaction
    }

    class Transaction {
        +string entry_reference  «unik nøgle pr. postering»
        +Amount transaction_amount
        +string credit_debit_indicator  «CRDT | DBIT»
        +string status  «BOOK»
        +string booking_date
        +string value_date
        +Amount balance_after_transaction
        +string[] remittance_information  «posteringstekst»
        +string? merchant_category_code
        +string? transaction_date
        +string? transaction_id
        +string? reference_number
        +string? reference_number_schema
        +string? exchange_rate
        +string? note
        +string? creditor_agent
        +string? debtor_agent
        +string? creditor_account_additional_identification
        +string? debtor_account_additional_identification
    }

    class BankTransactionCode {
        +string code  «CCRD | ICDT | RCDT | RDDT | MDOP | NTAV»
        +string sub_code  «POSD | POSC | AUTT | DMCT | PMDD | CHRG | ...»
        +string? description
    }

    class Party {
        +string name
        +PostalAddress? postal_address
        +string? organisation_id
        +string? private_id
        +string? contact_details
    }

    class PartyAccount {
        +string? iban
        +GenericIdentification? other
    }

    class Amount {
        +string currency
        +string amount  «decimaltal som streng»
    }

    AccountExport "1" *-- "1" Account : account
    AccountExport "1" *-- "2" Balance : balances
    AccountExport "1" *-- "*" Transaction : transactions

    Account "1" *-- "1" AccountIdentification : account_id
    Account "1" *-- "*" GenericIdentification : all_account_ids
    AccountIdentification "1" *-- "1" GenericIdentification : other

    Balance "1" *-- "1" Amount : balance_amount

    Transaction "1" *-- "1" Amount : transaction_amount
    Transaction "1" *-- "1" Amount : balance_after_transaction
    Transaction "1" *-- "1" BankTransactionCode : bank_transaction_code
    Transaction "1" *-- "0..1" Party : creditor
    Transaction "1" *-- "0..1" Party : debtor
    Transaction "1" *-- "0..1" PartyAccount : creditor_account
    Transaction "1" *-- "0..1" PartyAccount : debtor_account
    PartyAccount "1" *-- "0..1" GenericIdentification : other
```

## Noter

- `?` markerer felter, der er `null` i alle eller nogle af de hentede data. `PostalAddress` er altid `null` i data og er derfor ikke udfoldet.
- Beløb (`Amount.amount`) leveres som strenge, fx `"-123.45"`, for at undgå flydende-komma-afrunding. Fortegnet fremgår også af `credit_debit_indicator`.
- `Transaction.transaction_id` er `null` fra Danske Bank; brug `entry_reference` som unik nøgle, fx til deduplikering.
- `bank_transaction_code` følger ISO 20022 Bank Transaction Code: `CCRD`=kortbetaling, `ICDT`=afsendt overførsel, `RCDT`=modtaget overførsel, `RDDT`=Betalingsservice/direct debit, `MDOP`=gebyr, `NTAV`=ikke oplyst.
- `debtor_account.other.scheme_name = CPAN` bruges ved kortkøb (kortnummer, maskeret), `BANK` ved bankkonti.
