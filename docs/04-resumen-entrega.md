# Payment Reconciler — submission summary

**Problem.** An operations analyst needs to compare invoices against provider payment reports. Reports may contain amount or currency discrepancies, unknown invoice references or repeated events.

**Solution.** The application registers invoices, receives confirmed payment events and immediately compares invoice reference, amount and currency. An operations dashboard displays outcomes and audit history. This is a product hypothesis demonstrated with synthetic data.

**Decisions.** I used Python, Flask and SQLite for straightforward local execution. Routes, services, business rules and persistence have separate responsibilities. Reconciliation is a pure function. Amounts use integer minor units. A unique provider/event key prevents duplicate records; a repeated identifier with different data returns a conflict. Invoice updates, payment outcomes and audit history share one transaction.

**Scope and trade-offs.** The demo supports a simulated provider, one full payment per invoice, and COP and USD without conversion. Processing happens within the request, without a worker or queue. Failed writes roll back and the client may retry. The demo does not include authentication, actual payments, partial payments, refunds or manual discrepancy resolution.

**Validation.** Automated tests cover business rules, validation, concurrent duplicate requests, conflicts, rollback, persistence, API and page responses, and repeatable demo data with backup before reset.

**AI use.** I used an assistant to help scope the problem, generate implementation and tests, and draft documentation. The initial design was simplified to keep the flow focused and explainable. Before presenting, I will personally review the implementation.

**Next steps.** Validate the rules with operations, add discrepancy resolution and authentication before publishing, and consider PostgreSQL or asynchronous processing when actual traffic or integration needs justify them.
