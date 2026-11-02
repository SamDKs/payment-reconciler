# Payment Reconciler

A small application that matches confirmed payments against invoices using reference, amount and currency. An operations dashboard displays outcomes, explanations and audit history.

## Run locally

Requires Python 3.11 or newer. From `Challenge`:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-lock.txt
python -m pip install -e . --no-deps
flask --app app init-db
flask --app app seed-demo
flask --app app run --port 5050
```

Open http://127.0.0.1:5050. Only one process is needed. Payments are reconciled within the request. Initialization and demo loading can be repeated without duplicating records.

## Demo scenarios

| Record | Scenario | Outcome |
|---|---|---|
| PAY-001 / INV-001 | COP 150,000.00 received and expected | Matched |
| PAY-002 / INV-002 | COP 80,000.00 received; COP 90,000.00 expected | Amount discrepancy |
| PAY-003 / UNKNOWN | Unknown invoice reference | Unmatched |
| PAY-004 / INV-003 | USD 50,000.00 received; COP 50,000.00 expected | Currency discrepancy |
| PAY-005 / INV-001 | A distinct payment event for an already paid invoice | Requires review |
| INV-004 | COP 75,000.00 invoice without payments | Pending invoice |

The dashboard should show three pending invoices and one paid invoice. Payments are listed newest first. PAY-005 is a distinct event, not an identical retry. Demonstrate idempotency by resending PAY-001 with the same data.

To restore the demo:

```sh
flask --app app seed-demo --reset
```

**`--reset` replaces all records in the configured database**, after saving a SQLite backup named `backup-<timestamp>.sqlite3` in the same directory. Use it only on the local demo database. Existing backups are preserved. Without this option, existing records are retained.

## Architecture

- `entry_point`: HTTP API and HTML page routes.
- `application/services.py`: input validation and use-case coordination.
- `domain`: input models and a pure reconciliation function.
- `infrastructure`: SQLite connections, parameterized SQL and transactions.
- `templates` and `static`: dashboard presentation.

`create_app` wires the dependencies and registers Flask Blueprints. The service passes the reconciliation function to the repository so it can evaluate records read inside the transaction.

The `(provider, event_id)` unique constraint prevents duplicate events. Identical retries return the existing record; conflicting payloads return 409. Another unique index permits at most one matched payment per invoice. Invoice updates, payment outcomes and audit entries are committed together. On failure, all changes roll back and the client can retry safely. There is no worker, queue or automatic retry process.

## API

| Endpoint | Purpose |
|---|---|
| `POST /api/invoices` | Create an invoice, 201 |
| `GET /api/invoices` | List recent invoices |
| `POST /api/payment-events` | Register and reconcile, 201; identical retry, 200 |
| `GET /api/payment-events` | List recent payments |
| `GET /api/payment-events/<id>` | Payment outcome, current invoice and history |
| `GET /health` | Verify database readability |

List endpoints accept `limit` from 1 to 100. Payments also accept `result`: `matched`, `discrepancy`, `unmatched` or `requires_review`.

```sh
curl -i http://127.0.0.1:5050/api/payment-events \
  -H 'Content-Type: application/json' \
  -d '{"provider":"demo","event_id":"PAY-001","invoice_reference":"INV-001","amount_minor":15000000,"currency":"COP"}'
```

After demo loading, this returns 200 and `created: false`. The record count remains five.

Amounts use integer minor units: `15000000` means COP 150,000.00. COP and USD are modeled with two decimal places, without currency conversion. Invalid input returns 400; missing records 404; conflicts 409; database operational errors 503; unexpected errors 500 without exposing internal details.

## Tests

```sh
python -m pytest -q
```

Tests cover business rules, validation, simultaneous duplicates, conflicts, rollback, persistence, rendering, demo coverage and reset backups. Each test uses its own temporary SQLite database.

## Configuration and limitations

Optional variables: `RECONCILER_DATABASE` and `LOG_LEVEL`. `.env` is not loaded automatically. The default database is stored in `instance/` and excluded from version control. The initial schema creates missing tables but does not alter existing tables. An older database may retain unused columns.

This is a local demo with synthetic data and a simulated provider. It has no authentication or real banking integration. It supports one full payment per invoice, without partial payments, refunds, currency conversion or manual discrepancy resolution. Payments arriving before their invoices remain unmatched and are not automatically reprocessed. The payment detail shows the current invoice while its audit history preserves the original decision.

## Reading and presentation

Start with `entry_point/api.py`, then `application/services.py`, `domain/reconciliation.py`, `infrastructure/repositories.py` and `database.py`. Code comments and docstrings are in English.

[Implementation notes](docs/03-implementacion.md) · [Submission summary](docs/04-resumen-entrega.md) · [Diagrams](docs/05-diagramas.md) · [Five-minute video script](docs/06-guion-video.md)

The video narration is in English; private instructions about what to show remain in Spanish.

## Verification before submission

The release review passed 26 tests on Python 3.12 and Python 3.15. A built wheel was also installed into a clean Python 3.12 environment and exercised outside the source checkout: schema initialization, repeatable demo loading, dashboard and detail rendering, CSS, health and an identical payment retry.

The SQL schema is packaged with the application. `.gitignore` excludes virtual environments, databases, backups, build artifacts, local environment files and the original challenge instructions PDF.

Use **this directory as the repository root**, not its parent directory containing unrelated projects. Include the application, migrations, tests, dependency files, README and supporting documentation. The demo data is recreated with `seed-demo`; do not commit the local database. The video script is a rehearsal aid with Spanish stage directions; the application and submission summary are in English.

The application remains a local prototype: this review does not establish production readiness, authentication or a real provider integration.
