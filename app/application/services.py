"""Application use cases: validate input and coordinate persistence."""

from app.domain.models import InvoiceInput, PaymentInput, parse_input
from app.domain.reconciliation import reconcile


class ReconciliationService:
    """Coordinate operations using the repository passed to the constructor."""
    def __init__(self, repository):
        """Initialize this component with its required dependencies.

        Args:
            repository (SQLiteRepository): Repository for storing and querying invoices and payments.

        Returns:
            None: Initialize the object without returning a value.
        """
        self.repository = repository

    def create_invoice(self, data):
        """Store a new invoice and reject duplicate references.

        Args:
            data (dict): Input data to validate before persistence.

        Returns:
            dict: Stored invoice including its ID and initial status.

        Raises:
            ConflictError: If the invoice reference already exists.
            ValidationError: If the input data does not satisfy the contract.
        """
        invoice = parse_input(data, InvoiceInput)
        return self.repository.create_invoice(invoice)

    def receive_payment(self, data):
        """Validate or store the payment and return its outcome without duplicate effects.

        Args:
            data (dict): Input data to validate before persistence.

        Returns:
            tuple[dict, bool]: Payment with its outcome and a flag: True if created, False if it already existed.

        Raises:
            ConflictError: If the same provider and event already exist with different data.
            ValidationError: If the input data does not satisfy the contract.
        """
        payment = parse_input(data, PaymentInput)
        return self.repository.receive_payment(payment, reconcile)
