"""HTTP flow tests using a real SQLite database and isolated data."""

from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

import pytest

from app import create_app


def test_complete_flow_and_duplicate(client, invoice, payment):
    """Verify the successful flow and that repeated events do not repeat effects.

    Args:
        client (FlaskClient): Test client for sending HTTP requests without starting a server.
        invoice (dict): Sample input provided by a pytest fixture.
        payment (dict): Sample input provided by a pytest fixture.

    Returns:
        None: Return no data; assertions verify the expected behavior.
    """
    assert client.post("/api/invoices", json=invoice).status_code == 201
    response = client.post("/api/payment-events", json=payment)
    assert response.status_code == 201
    location = response.headers["Location"]
    assert client.post("/api/payment-events", json=payment).json["created"] is False
    result = client.get(location).json
    assert result["result"] == "matched"
    assert result["invoice"]["status"] == "paid"
    assert len(result["history"]) == 2
    duplicate = client.post("/api/payment-events", json=payment)
    assert duplicate.status_code == 200
    assert len(client.get(location).json["history"]) == 2
    assert len(client.get("/api/payment-events").json) == 1


def test_conflict(client, invoice, payment):
    """Reject duplicate references and repeated events with different content.

    Args:
        client (FlaskClient): Test client for sending HTTP requests without starting a server.
        invoice (dict): Sample input provided by a pytest fixture.
        payment (dict): Sample input provided by a pytest fixture.

    Returns:
        None: Return no data; assertions verify the expected behavior.
    """
    client.post("/api/invoices", json=invoice)
    assert client.post("/api/invoices", json=invoice).status_code == 409
    client.post("/api/payment-events", json=payment)
    assert client.post("/api/payment-events", json=payment | {"amount_minor": 42}).status_code == 409


@pytest.mark.parametrize("change,expected", [({"amount_minor": 42}, "discrepancy"), ({"currency": "USD"}, "discrepancy"), ({"invoice_reference": "missing"}, "unmatched")])
def test_differences_do_not_pay_invoice(client, invoice, payment, change, expected):
    """Verify discrepancies do not mark the invoice as paid.

    Args:
        client (FlaskClient): Test client for sending HTTP requests without starting a server.
        invoice (dict): Sample input provided by a pytest fixture.
        payment (dict): Sample input provided by a pytest fixture.
        change (dict): Payment fields overridden for this test case.
        expected (str): Reconciliation outcome expected for this test case.

    Returns:
        None: Return no data; assertions verify the expected behavior.
    """
    client.post("/api/invoices", json=invoice)
    case_payment = payment | change  # Copy the payment and override only this test case's fields.
    response = client.post("/api/payment-events", json=case_payment)
    assert client.get(response.headers["Location"]).json["result"] == expected
    assert client.get("/api/invoices").json[0]["status"] == "pending"


def test_second_payment_requires_review(client, invoice, payment):
    """Send a distinct payment for a paid invoice and require review.

    Args:
        client (FlaskClient): Test client for sending HTTP requests without starting a server.
        invoice (dict): Sample input provided by a pytest fixture.
        payment (dict): Sample input provided by a pytest fixture.

    Returns:
        None: Return no data; assertions verify the expected behavior.
    """
    client.post("/api/invoices", json=invoice)
    client.post("/api/payment-events", json=payment)
    client.post("/api/payment-events", json=payment | {"event_id": "second"})
    assert client.get("/api/payment-events").json[0]["result"] == "requires_review"


def test_transaction_rolls_back_before_commit(client, app, invoice, payment):
    """Inject a failure and verify that no partial changes are persisted.

    Args:
        client (FlaskClient): Test client for sending HTTP requests without starting a server.
        app (Flask): Test application configured with a temporary database.
        invoice (dict): Sample input provided by a pytest fixture.
        payment (dict): Sample input provided by a pytest fixture.

    Returns:
        None: Return no data; assertions verify the expected behavior.
    """
    client.post("/api/invoices", json=invoice)
    repository = app.extensions["repository"]
    original_audit = repository.audit

    def fail_on_completion(connection, payment_id, action, detail):
        """Simulate a failure before commit to verify rollback.

        Args:
            connection (sqlite3.Connection): Current transaction connection shared by all writes in the operation.
            payment_id (int): Internal database ID of the payment.
            action (str): Name of the action appended to the audit history.
            detail (str): Explanation of the recorded audit action.

        Returns:
            None: Record normal actions or raise the simulated failure at payment completion.

        Raises:
            RuntimeError: When recording the completed action, to test transaction rollback.
        """
        if action == "completed":
            raise RuntimeError("failure before commit")
        original_audit(connection, payment_id, action, detail)

    with patch.object(repository, "audit", side_effect=fail_on_completion):  # Temporarily replace the audit write operation.
        assert client.post("/api/payment-events", json=payment).status_code == 500
    assert client.get("/api/invoices").json[0]["status"] == "pending"
    assert client.get("/api/payment-events").json == []
    assert client.post("/api/payment-events", json=payment).status_code == 201


def test_data_survives_restart(app, client, invoice, payment):
    """Recreate the application with the same database file to verify persistence.

    Args:
        app (Flask): Test application configured with a temporary database.
        client (FlaskClient): Test client for sending HTTP requests without starting a server.
        invoice (dict): Sample input provided by a pytest fixture.
        payment (dict): Sample input provided by a pytest fixture.

    Returns:
        None: Return no data; assertions verify the expected behavior.
    """
    client.post("/api/invoices", json=invoice)
    client.post("/api/payment-events", json=payment)
    restarted = create_app({"TESTING": True, "DATABASE": app.config["DATABASE"]})
    assert restarted.test_client().get("/api/invoices").json[0]["status"] == "paid"


def test_simultaneous_duplicate_reception(app, payment):
    """Verify that simultaneous requests create only one payment.

    Args:
        app (Flask): Test application configured with a temporary database.
        payment (dict): Sample input provided by a pytest fixture.

    Returns:
        None: Return no data; assertions verify the expected behavior.
    """
    def receive(_):
        """Send the same payment from a separate client to test concurrency.

        Args:
            _ (int): Iteration value; unused because both requests send the same payment.

        Returns:
            int: HTTP status code returned by the payment endpoint.
        """
        with app.test_client() as client:
            return client.post("/api/payment-events", json=payment).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:  # Simulate two simultaneous requests.
        assert sorted(pool.map(receive, range(2))) == [200, 201]  # One request creates the payment and the other retrieves it.
    assert len(app.test_client().get("/api/payment-events").json) == 1


@pytest.mark.parametrize("value", [True, 0, -1, 12.5, "100", None, 10**15])
def test_invalid_amount(client, invoice, value):
    """Reject invalid amounts without creating an invoice.

    Args:
        client (FlaskClient): Test client for sending HTTP requests without starting a server.
        invoice (dict): Sample input provided by a pytest fixture.
        value (object): Invalid value submitted as the invoice amount.

    Returns:
        None: Return no data; assertions verify the expected behavior.
    """
    assert client.post("/api/invoices", json=invoice | {"amount_minor": value}).status_code == 400


def test_normalization_and_invalid_contract(client, invoice, payment):
    """Verify currency normalization and invalid input rejection.

    Args:
        client (FlaskClient): Test client for sending HTTP requests without starting a server.
        invoice (dict): Sample input provided by a pytest fixture.
        payment (dict): Sample input provided by a pytest fixture.

    Returns:
        None: Return no data; assertions verify the expected behavior.
    """
    assert client.post("/api/invoices", json=invoice | {"currency": " cop "}).status_code == 201
    assert client.post("/api/payment-events", json=payment | {"provider": "other"}).status_code == 400
    assert client.post("/api/payment-events", json=payment | {"currency": "EUR"}).status_code == 400
    assert client.post("/api/invoices", json={}).status_code == 400
    assert client.post("/api/invoices", json=[]).status_code == 400
    assert client.post("/api/invoices", data="{", content_type="application/json").status_code == 400


def test_read_endpoints_and_panel(client, app):
    """Verify repeatable demo loading, queries, filters and page rendering.

    Args:
        client (FlaskClient): Test client for sending HTTP requests without starting a server.
        app (Flask): Test application configured with a temporary database.

    Returns:
        None: Return no data; assertions verify the expected behavior.
    """
    runner = app.test_cli_runner()
    assert runner.invoke(args=["seed-demo"]).exit_code == 0
    assert runner.invoke(args=["seed-demo"]).exit_code == 0
    assert client.get("/health").status_code == 200
    assert client.get("/").status_code == 200
    assert client.get("/payments/1").status_code == 200
    assert client.get("/api/payment-events/999").status_code == 404
    assert client.get("/api/payment-events?result=matched").json[0]["result"] == "matched"
    assert client.get("/api/payment-events?result=invalid").status_code == 400
    assert client.get("/api/invoices?limit=101").status_code == 400
    assert client.get("/api/invoices?limit=oops").status_code == 400


def test_demo_covers_all_results_and_reset_keeps_backup(app, client):
    """Verify demo outcome coverage and data backup before resetting.

    Args:
        app (Flask): Application configured with a temporary database.
        client (FlaskClient): Test client for querying the demo records.

    Returns:
        None: Verify counts, outcomes and backup existence.
    """
    from pathlib import Path
    import sqlite3

    runner = app.test_cli_runner()
    assert runner.invoke(args=["seed-demo"]).exit_code == 0
    assert runner.invoke(args=["seed-demo"]).exit_code == 0
    events = client.get("/api/payment-events").json
    assert len(events) == 5
    assert {event["result"] for event in events} == {"matched", "discrepancy", "unmatched", "requires_review"}
    invoices = client.get("/api/invoices").json
    assert len(invoices) == 4
    assert sum(invoice["status"] == "paid" for invoice in invoices) == 1
    assert "The payment currency" in next(event for event in events if event["event_id"] == "PAY-004")["reason"]
    assert "Requires review" in client.get("/").text
    assert runner.invoke(args=["seed-demo", "--reset"]).exit_code == 0
    backups = list(Path(app.config["DATABASE"]).parent.glob("backup-*.sqlite3"))
    assert len(backups) == 1
    with sqlite3.connect(backups[0]) as backup:
        assert backup.execute("SELECT COUNT(*) FROM payment_events").fetchone()[0] == 5
    assert len(client.get("/api/payment-events").json) == 5


def test_two_distinct_payments_cannot_match_the_same_invoice(app, client, invoice, payment):
    """Verify concurrent distinct events cannot both pay the same invoice.

    Args:
        app (Flask): Application with a temporary SQLite database.
        client (FlaskClient): Client used to create the invoice and read outcomes.
        invoice (dict): Sample invoice input.
        payment (dict): Sample payment input.

    Returns:
        None: Assert one match, one review and a paid invoice.
    """
    client.post("/api/invoices", json=invoice)

    def send(index):
        """Submit a distinct event from an independent client.

        Args:
            index (int): Suffix that makes the event identifier unique.

        Returns:
            int: HTTP status returned by the request.
        """
        with app.test_client() as concurrent_client:
            return concurrent_client.post(
                "/api/payment-events", json=payment | {"event_id": f"parallel-{index}"}
            ).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert list(pool.map(send, range(2))) == [201, 201]
    assert sorted(row["result"] for row in client.get("/api/payment-events").json) == ["matched", "requires_review"]
    assert client.get("/api/invoices").json[0]["status"] == "paid"


def test_reordered_normalized_retry_is_not_a_conflict(client, invoice, payment):
    """Verify JSON key order and normalized whitespace do not create conflicts.

    Args:
        client (FlaskClient): HTTP test client.
        invoice (dict): Sample invoice input.
        payment (dict): Sample payment input.

    Returns:
        None: Assert an identical normalized retry returns the stored event.
    """
    client.post("/api/invoices", json=invoice)
    client.post("/api/payment-events", json=payment)
    retry = dict(reversed(list(payment.items())))
    retry.update(currency=" cop ", event_id=" PAY-001 ")
    response = client.post("/api/payment-events", json=retry)
    assert response.status_code == 200
    assert response.json["created"] is False
    assert len(client.get("/api/payment-events/1").json["history"]) == 2
