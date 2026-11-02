# Implementation notes

Payments are reconciled within the HTTP request. There is no background worker, queue or automatic retry process.

## Code walkthrough

1. `entry_point/api.py` receives JSON and returns an HTTP response.
2. `application/services.py` validates input and coordinates persistence.
3. `infrastructure/repositories.py` opens a transaction, checks duplicates and retrieves the invoice.
4. `domain/reconciliation.py` compares the records and returns an outcome and reason.
5. The repository commits the invoice update, payment outcome and audit entries together.
6. `entry_point/web.py` queries records and renders HTML templates.

## Main decisions

- Flask and SQLite keep local setup small and reproducible.
- Immediate processing fits a short comparison without external network calls.
- Integer minor units avoid floating-point money arithmetic.
- Unique event identifiers protect against repeated provider reports.
- Transactions prevent partial writes.
- Pure business rules can be tested independently of Flask and SQLite.

On failure, the transaction rolls back. The client can resend the same event safely. This guarantee covers effects inside this database, not future external side effects.

## AI use

An AI assistant supported problem scoping, code generation, tests and documentation. The initial design was simplified to make the implementation easier to understand and explain. The candidate should personally review the code and describe the use of AI transparently.
