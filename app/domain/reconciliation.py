"""Reconciliation rules independent of Flask and database access."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Decision:
    """Comparison outcome and explanation for operations."""
    result: str
    reason: str


def reconcile(payment, invoice):
    """Return an outcome and reason without modifying the inputs.

    Args:
        payment (dict | sqlite3.Row): Confirmed payment fields to compare against the invoice.
        invoice (dict | sqlite3.Row | None): Expected invoice, or None if its reference is unknown.

    Returns:
        Decision: Comparison outcome and explanation shown to the user.
    """
    if invoice is None:
        return Decision("unmatched", "No invoice exists for this reference.")
    if invoice["status"] == "paid":
        return Decision("requires_review", "The invoice was already paid by another event.")
    if payment["currency"] != invoice["currency"]:
        return Decision("discrepancy", "The payment currency does not match the invoice.")
    if payment["amount_minor"] != invoice["amount_minor"]:
        return Decision("discrepancy", "The payment amount does not match the invoice.")
    return Decision("matched", "Reference, amount and currency match.")
