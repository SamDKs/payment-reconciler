"""Business rule tests without database access."""

import pytest

from app.domain.reconciliation import reconcile


# Run the same test for several input combinations.
@pytest.mark.parametrize("changes,invoice_changes,expected", [
    ({}, {}, "matched"),
    ({"amount_minor": 1}, {}, "discrepancy"),
    ({"currency": "USD"}, {}, "discrepancy"),
    ({}, {"status": "paid"}, "requires_review"),
])
def test_business_decisions(payment, invoice, changes, invoice_changes, expected):
    """Verify matching payments, discrepancies and already paid invoices.

    Args:
        payment (dict): Sample input provided by a pytest fixture.
        invoice (dict): Sample input provided by a pytest fixture.
        changes (dict): Payment field overrides used to evaluate a business scenario.
        invoice_changes (dict): Invoice field overrides for this test case.
        expected (str): Reconciliation outcome expected for this test case.

    Returns:
        None: Return no data; assertions verify the expected behavior.
    """
    assert reconcile(payment | changes, invoice | {"status": "pending"} | invoice_changes).result == expected


def test_unknown_reference(payment):
    """Verify that a payment without an invoice remains unmatched.

    Args:
        payment (dict): Sample input provided by a pytest fixture.

    Returns:
        None: Return no data; assertions verify the expected behavior.
    """
    assert reconcile(payment, None).result == "unmatched"
