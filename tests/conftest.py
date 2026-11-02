"""Shared test fixtures; each database is temporary."""

import pytest

from app import create_app


@pytest.fixture
def app(tmp_path):
    """Create an application with a new database in pytest's temporary directory.

    Args:
        tmp_path (Path): Temporary directory created by pytest to isolate test data.

    Returns:
        Flask: Isolated application used by the tests.
    """
    application = create_app({"TESTING": True, "DATABASE": str(tmp_path / "test.sqlite3")})
    application.extensions["database"].initialize()
    return application


@pytest.fixture
def client(app):
    """Provide an HTTP test client without starting a server.

    Args:
        app (Flask): Test application configured with a temporary database.

    Returns:
        FlaskClient: HTTP client connected to the test application.
    """
    return app.test_client()


@pytest.fixture
def invoice():
    """Return a sample invoice with an amount in minor units.

    Args:
        None.

    Returns:
        dict: Sample invoice for COP 150,000.00 with reference INV-001.
    """
    return {"reference": "INV-001", "amount_minor": 15000000, "currency": "COP"}


@pytest.fixture
def payment():
    """Return a sample payment matching the shared invoice fixture.

    Args:
        None.

    Returns:
        dict: Sample payment matching the invoice reference, amount and currency.
    """
    return {"provider": "demo", "event_id": "PAY-001", "invoice_reference": "INV-001", "amount_minor": 15000000, "currency": "COP"}
