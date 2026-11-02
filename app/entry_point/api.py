"""JSON routes for creating and querying invoices and payments."""

from flask import Blueprint, current_app, jsonify, request, url_for

from app.domain.exceptions import ValidationError

api = Blueprint("api", __name__)
RESULTS = {"matched", "unmatched", "discrepancy", "requires_review"}


def repository():
    """Retrieve the repository configured by create_app for this application.

    Args:
        None.

    Returns:
        SQLiteRepository: Repository associated with the Flask application handling the request.
    """
    return current_app.extensions["repository"]


def query_options():
    """Validate the outcome filter and list limit.

    Args:
        None. Request data is read from Flask's request context.

    Returns:
        tuple[str | None, int]: Validated outcome filter and list limit.

    Raises:
        ValidationError: If the requested outcome filter or list limit is invalid.
    """
    result = request.args.get("result") or None
    if result is not None and result not in RESULTS:
        raise ValidationError("Invalid outcome filter.")
    try:
        limit = int(request.args.get("limit", 100))  # HTTP query parameters arrive as strings.
    except ValueError as error:
        raise ValidationError("limit must be an integer between 1 and 100.") from error
    if not 1 <= limit <= 100:
        raise ValidationError("limit must be an integer between 1 and 100.")
    return result, limit


@api.get("/health")
def health():
    """Check that the application can query the database.

    Args:
        None. Request data is read from Flask's request context.

    Returns:
        dict: Status ok when the database query succeeds.
    """
    repository().summary()
    return {"status": "ok"}


@api.post("/api/invoices")
def create_invoice():
    """Store a new invoice and reject duplicate references.

    Args:
        None. Request data is read from Flask's request context.

    Returns:
        tuple[Response, int]: Created invoice JSON and HTTP status code 201.

    Raises:
        ConflictError: If the invoice reference already exists.
    """
    return jsonify(current_app.extensions["service"].create_invoice(request.get_json())), 201


@api.get("/api/invoices")
def invoices():
    """Return invoices as a JSON list.

    Args:
        None. Request data is read from Flask's request context.

    Returns:
        Response: JSON response containing the requested invoices.
    """
    _, limit = query_options()
    return jsonify(repository().list_invoices(limit))


@api.post("/api/payment-events")
def receive_payment():
    """Validate or store the payment and return its outcome without duplicate effects.

    Args:
        None. Request data is read from Flask's request context.

    Returns:
        tuple[Response, int, dict]: Payment JSON, status code 201 or 200 and a Location header pointing to its detail URL.

    Raises:
        ConflictError: If the same provider and event already exist with different data.
    """
    payment, created = current_app.extensions["service"].receive_payment(request.get_json())
    location = url_for("api.payment_detail", payment_id=payment["id"])
    status = 201 if created else 200  # New record: 201; repeated event: 200.
    return jsonify({**payment, "created": created, "url": location}), status, {"Location": location}


@api.get("/api/payment-events")
def payments():
    """Return payments as JSON with an optional filter.

    Args:
        None. Request data is read from Flask's request context.

    Returns:
        Response: JSON response containing the requested payments.
    """
    result, limit = query_options()
    return jsonify(repository().list_payments(result, limit))


@api.get("/api/payment-events/<int:payment_id>")
def payment_detail(payment_id):
    """Return a payment outcome and audit history.

    Args:
        payment_id (int): Internal database ID of the payment.

    Returns:
        Response: JSON response containing payment details and audit history.
    """
    return jsonify(repository().get_payment(payment_id))
