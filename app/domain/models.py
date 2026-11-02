"""Invoice and payment input models and their validation."""

from dataclasses import dataclass, fields

from app.domain.exceptions import ValidationError


@dataclass(frozen=True)
class InvoiceInput:
    """Invoice fields; frozen prevents changes after construction."""
    reference: str
    amount_minor: int
    currency: str


@dataclass(frozen=True)
class PaymentInput:
    """Confirmed payment fields and a stable provider event identifier."""
    provider: str
    event_id: str
    invoice_reference: str
    amount_minor: int
    currency: str


def parse_input(data, model):
    """Validate fields, normalize text and construct the requested input model.

    Args:
        data (dict): Input data to validate before persistence.
        model (type[InvoiceInput] | type[PaymentInput]): Input model defining the expected fields.

    Returns:
        InvoiceInput | PaymentInput: Input model constructed from validated and normalized fields.

    Raises:
        ValidationError: If fields are missing, unexpected or contain invalid values.
    """
    if not isinstance(data, dict):
        raise ValidationError("A JSON object is required.")
    field_names = [field.name for field in fields(model)]  # Read the field names defined by the input model.
    if set(data) != set(field_names):  # Reject both missing and unexpected fields.
        raise ValidationError(f"Required fields, with no additional fields: {', '.join(field_names)}.")
    normalized = {}
    for name in field_names:
        value = data[name]
        if name == "amount_minor":
            if type(value) is not int or not 0 < value <= 10**14:  # An exact type check rejects True and False, which inherit from int.
                raise ValidationError("amount_minor must be a positive integer no greater than 100000000000000.")
        else:
            if not isinstance(value, str) or not 1 <= len(value.strip()) <= 100:
                raise ValidationError(f"{name} must contain between 1 and 100 characters.")
            value = value.strip()  # Remove leading and trailing whitespace only.
            if name == "currency":
                value = value.upper()
                if value not in {"COP", "USD"}:
                    raise ValidationError("Supported currencies: COP and USD.")
            if name == "provider" and value != "demo":
                raise ValidationError("The supported provider in this demo is 'demo'.")
        normalized[name] = value
    return model(**normalized)  # Construct InvoiceInput or PaymentInput from validated fields.
