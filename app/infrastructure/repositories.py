"""SQL queries and persistence for invoices, payments and audit history."""

from dataclasses import asdict
from datetime import datetime, timezone
import sqlite3

from app.domain.exceptions import ConflictError, NotFoundError


def utc_now():
    """Generate a UTC timestamp for ordering and auditing records.

    Args:
        None.

    Returns:
        str: Current UTC date and time in ISO 8601 format.
    """
    return datetime.now(timezone.utc).isoformat()


class SQLiteRepository:
    """Group persistence operations into transactions."""
    def __init__(self, database):
        """Initialize this component with its required dependencies.

        Args:
            database (Database): SQLite connection and transaction manager.

        Returns:
            None: Initialize the object without returning a value.
        """
        self.database = database

    @staticmethod
    def audit(connection, payment_id, action, detail):
        """Append an audit entry within the payment transaction.

        Args:
            connection (sqlite3.Connection): Current transaction connection shared by all writes in the operation.
            payment_id (int): Internal database ID of the payment.
            action (str): Name of the action appended to the audit history.
            detail (str): Explanation of the recorded audit action.

        Returns:
            None: Insert an audit entry; the surrounding transaction controls the commit.
        """
        connection.execute(
            "INSERT INTO audit_entries(payment_event_id,action,detail,created_at) VALUES (?,?,?,?)",
            (payment_id, action, detail, utc_now()),
        )

    def create_invoice(self, invoice):
        """Store a new invoice and reject duplicate references.

        Args:
            invoice (InvoiceInput): Validated invoice containing its reference, amount in minor units and currency.

        Returns:
            dict: Stored invoice including its ID and initial status.

        Raises:
            ConflictError: If the invoice reference already exists.
        """
        try:
            with self.database.transaction() as connection:
                cursor = connection.execute(
                    "INSERT INTO invoices(reference,amount_minor,currency,created_at) VALUES (?,?,?,?)",
                    (invoice.reference, invoice.amount_minor, invoice.currency, utc_now()),
                )
                return dict(connection.execute("SELECT * FROM invoices WHERE id=?", (cursor.lastrowid,)).fetchone())
        except sqlite3.IntegrityError as error:
            # Only duplicate references are business conflicts; other constraints indicate a bug.
            if getattr(error, "sqlite_errorname", None) != "SQLITE_CONSTRAINT_UNIQUE":
                raise
            raise ConflictError("The invoice reference already exists.") from error

    def receive_payment(self, payment, decide):
        """Validate or store the payment and return its outcome without duplicate effects.

        Args:
            payment (PaymentInput): Validated payment containing provider event identification and reconciliation fields.
            decide (Callable): Function comparing payment and invoice and returning a Decision.

        Returns:
            tuple[dict, bool]: Payment with its outcome and a flag: True if created, False if it already existed.

        Raises:
            ConflictError: If the same provider and event already exist with different data.
        """
        values = asdict(payment)  # Convert the input model into a dictionary for field comparison.
        with self.database.transaction() as connection:
            existing = connection.execute(
                "SELECT * FROM payment_events WHERE provider=? AND event_id=?",
                (payment.provider, payment.event_id),
            ).fetchone()
            if existing:
                if any(existing[key] != value for key, value in values.items()):  # A single different field is enough to cause a conflict.
                    raise ConflictError("The event identifier already exists with different data.")
                return dict(existing), False  # False indicates that no new payment was created.
            # Bind values through ? placeholders instead of concatenating user input into SQL.
            cursor = connection.execute(
                "INSERT INTO payment_events(provider,event_id,invoice_reference,amount_minor,currency,created_at) VALUES (?,?,?,?,?,?)",
                (payment.provider, payment.event_id, payment.invoice_reference, payment.amount_minor, payment.currency, utc_now()),
            )
            # lastrowid identifies the record just inserted by this connection.
            self.audit(connection, cursor.lastrowid, "received", "Confirmed payment received.")
            invoice = connection.execute(
                "SELECT * FROM invoices WHERE reference=?", (payment.invoice_reference,)
            ).fetchone()
            decision = decide(values, invoice)  # Apply the pure business rule selected by the service.
            if decision.result == "matched":
                connection.execute(
                    "UPDATE invoices SET status='paid',paid_at=? WHERE id=?",
                    (utc_now(), invoice["id"]),
                )
            connection.execute(
                "UPDATE payment_events SET result=?,reason=?,invoice_id=?,completed_at=? WHERE id=?",
                (decision.result, decision.reason, invoice["id"] if invoice else None, utc_now(), cursor.lastrowid),
            )
            self.audit(connection, cursor.lastrowid, "completed", decision.reason)
            row = connection.execute("SELECT * FROM payment_events WHERE id=?", (cursor.lastrowid,)).fetchone()
            return dict(row), True  # True lets the API return 201 for a newly created record.

    def list_invoices(self, limit=100):
        """Fetch the most recent invoices up to the requested limit.

        Args:
            limit (int): Maximum number of records to return; defaults to 100.

        Returns:
            list[dict]: Invoices ordered from newest to oldest.
        """
        with self.database.connection() as connection:
            # Convert SQLite rows into dictionaries for JSON serialization.
            return [dict(row) for row in connection.execute("SELECT * FROM invoices ORDER BY id DESC LIMIT ?", (limit,))]

    def list_payments(self, result=None, limit=100):
        """Fetch recent payments with an optional outcome filter.

        Args:
            result (str | None): Outcome filter; None includes all outcomes.
            limit (int): Maximum number of records to return; defaults to 100.

        Returns:
            list[dict]: Recent payments matching the requested filter.
        """
        with self.database.connection() as connection:
            # Convert SQLite rows into dictionaries for JSON serialization.
            return [dict(row) for row in connection.execute(
                "SELECT * FROM payment_events WHERE (? IS NULL OR result=?) ORDER BY id DESC LIMIT ?",  # NULL disables the optional filter.
                (result, result, limit),
            )]

    def get_payment(self, payment_id):
        """Fetch a payment with its audit history and current invoice, if available.

        Args:
            payment_id (int): Internal database ID of the payment.

        Returns:
            dict: Payment fields, audit history and current invoice if available.

        Raises:
            NotFoundError: If the requested payment ID does not exist.
        """
        with self.database.connection() as connection:
            row = connection.execute("SELECT * FROM payment_events WHERE id=?", (payment_id,)).fetchone()
            if row is None:
                raise NotFoundError("The payment does not exist.")
            payment = dict(row)
            # Order audit entries by insertion, from the first action to the last.
            payment["history"] = [dict(item) for item in connection.execute(
                "SELECT action,detail,created_at FROM audit_entries WHERE payment_event_id=? ORDER BY id", (payment_id,)
            )]
            invoice = connection.execute("SELECT * FROM invoices WHERE reference=?", (payment["invoice_reference"],)).fetchone()
            payment["invoice"] = dict(invoice) if invoice else None
            return payment

    def summary(self):
        """Count pending and paid invoices for the dashboard cards.

        Args:
            None.

        Returns:
            dict: Invoice counts grouped by status under the invoices key.
        """
        with self.database.connection() as connection:
            return {
                "invoices": dict(connection.execute("SELECT status,COUNT(*) FROM invoices GROUP BY status").fetchall()),
            }
