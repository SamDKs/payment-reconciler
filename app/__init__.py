"""Create the application, wire dependencies and register commands and error handlers."""

import logging
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import click
from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException

from app.application.services import ReconciliationService
from app.config import settings
from app.domain.exceptions import ConflictError, NotFoundError, ValidationError
from app.entry_point.api import api
from app.entry_point.web import web
from app.infrastructure.database import Database
from app.infrastructure.repositories import SQLiteRepository


def create_app(test_config=None):
    """Build Flask and allow configuration overrides in tests.

    Args:
        test_config (dict | None): Optional overrides for default settings, such as the temporary test database.

    Returns:
        Flask: Application with routes, services, repository, CLI commands and error handlers.
    """
    app = Flask(__name__)
    app.config.update(settings())
    if test_config:
        app.config.update(test_config)  # Tests use a temporary database instead of the demo database.
    logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
    database = Database(app.config["DATABASE"])
    repository = SQLiteRepository(database)
    app.extensions.update(database=database, repository=repository, service=ReconciliationService(repository))
    app.register_blueprint(api)
    app.register_blueprint(web)
    # Display readable labels in the UI while keeping stable API outcome codes.
    app.jinja_env.globals.update(
        result_labels={
            "matched": "Matched", "discrepancy": "Discrepancy",
            "unmatched": "Unmatched", "requires_review": "Requires review",
        },
        action_labels={"received": "Payment received", "completed": "Reconciliation completed"},
    )

    @app.cli.command("init-db")
    def init_db():
        """Create missing tables without deleting existing records.

        Args:
            None.

        Returns:
            None: Create missing tables and print a CLI message.
        """
        database.initialize()
        click.echo("Database initialized.")

    @app.cli.command("seed-demo")
    @click.option("--reset", is_flag=True, help="Back up the current database and replace its records with demo data.")
    def seed_demo(reset):
        """Load five payments covering every reconciliation outcome.

        Args:
            reset (bool): If True, back up the database and clear its records before loading the demo.

        Returns:
            None: Store demo records and print a CLI message.
        """
        if reset:
            stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
            backup_path = Path(database.path).with_name(f"backup-{stamp}.sqlite3")
            with database.connection() as source:
                with sqlite3.connect(backup_path) as backup:
                    source.backup(backup)  # Include committed changes stored in the WAL file.
            with database.transaction() as connection:
                # Delete dependent records first to satisfy foreign key constraints.
                connection.execute("DELETE FROM audit_entries")
                connection.execute("DELETE FROM payment_events")
                connection.execute("DELETE FROM invoices")
            click.echo(f"Backup saved to {backup_path}")

        service = app.extensions["service"]
        for reference, amount in [
            ("INV-001", 15000000),  # COP 150,000: receives a matching payment.
            ("INV-002", 9000000),   # COP 90,000: receives only COP 80,000.
            ("INV-003", 5000000),   # COP 50,000: receives a payment in a different currency.
            ("INV-004", 7500000),   # COP 75,000: remains pending without a payment.
        ]:
            try:
                service.create_invoice({"reference": reference, "amount_minor": amount, "currency": "COP"})
            except ConflictError:
                pass  # Allow repeated demo loading without duplicating invoices.
        for event_id, reference, amount, currency in [
            ("PAY-001", "INV-001", 15000000, "COP"),
            ("PAY-002", "INV-002", 8000000, "COP"),
            ("PAY-003", "UNKNOWN", 1000000, "COP"),
            ("PAY-004", "INV-003", 5000000, "USD"),
            ("PAY-005", "INV-001", 15000000, "COP"),  # A different event for an already paid invoice.
        ]:
            service.receive_payment({
                "provider": "demo", "event_id": event_id,
                "invoice_reference": reference, "amount_minor": amount, "currency": currency,
            })
        click.echo("Demo loaded: four invoices and five sample payments.")

    @app.template_filter("money")
    def money(value):
        """Format integer minor units with two decimal places for the dashboard.

        Args:
            value (int): Amount expressed in integer minor units.

        Returns:
            str: Amount formatted with thousands separators and two decimal places without float arithmetic.
        """
        whole, fraction = divmod(value, 100)  # Separate whole units and cents without using float.
        return f"{whole:,}.{fraction:02d}"  # Add thousands separators and two decimal places.

    @app.errorhandler(ValidationError)
    def validation_error(error):
        """Return 400 when input does not satisfy the contract.

        Args:
            error (Exception): Caught exception to translate into an HTTP response.

        Returns:
            tuple[Response, int]: JSON error message and its HTTP status code.
        """
        return jsonify(error={"code": "invalid_input", "message": str(error)}), 400

    @app.errorhandler(ConflictError)
    def conflict_error(error):
        """Return 409 when a reference or identifier conflicts.

        Args:
            error (Exception): Caught exception to translate into an HTTP response.

        Returns:
            tuple[Response, int]: JSON error message and its HTTP status code.
        """
        return jsonify(error={"code": "conflict", "message": str(error)}), 409

    @app.errorhandler(NotFoundError)
    def not_found(error):
        """Return 404 when the requested record does not exist.

        Args:
            error (Exception): Caught exception to translate into an HTTP response.

        Returns:
            tuple[Response, int]: JSON error message and its HTTP status code.
        """
        return jsonify(error={"code": "not_found", "message": str(error)}), 404

    @app.errorhandler(HTTPException)
    def http_error(error):
        """Preserve Flask's HTTP status code and return a JSON error.

        Args:
            error (Exception): Caught exception to translate into an HTTP response.

        Returns:
            tuple[Response, int]: JSON error message and its HTTP status code.
        """
        return jsonify(error={"code": error.name, "message": error.description}), error.code

    @app.errorhandler(Exception)
    def unexpected_error(error):
        """Log technical details and return a safe public error message.

        Args:
            error (Exception): Caught exception to translate into an HTTP response.

        Returns:
            tuple[Response, int]: JSON error message and its HTTP status code.
        """
        app.logger.exception("request_failed")  # Log the technical traceback without exposing it in the response.
        status = 503 if isinstance(error, sqlite3.OperationalError) else 500
        return jsonify(error={"code": "service_unavailable" if status == 503 else "internal_error", "message": "The operation could not be completed."}), status

    return app
