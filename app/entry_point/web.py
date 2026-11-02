"""Routes for querying data and rendering the HTML dashboard."""

from flask import Blueprint, render_template

from app.entry_point.api import query_options, repository

# Group web pages for registration in create_app.
web = Blueprint("web", __name__)


@web.get("/")
def dashboard():
    """Gather the queries needed to render the dashboard.

    Args:
        None.

    Returns:
        str: Dashboard HTML containing summary cards, invoices and payments.
    """
    result, limit = query_options()  # Reuse the API query parameter validation.
    data = repository()
    return render_template(
        "dashboard.html",
        summary=data.summary(),
        invoices=data.list_invoices(limit),
        payments=data.list_payments(result, limit),
        selected=result,  # Keep the selected filter after reloading.
    )


@web.get("/payments/<int:payment_id>")
def detail(payment_id):
    """Render the payment detail page.

    Args:
        payment_id (int): Internal database ID of the payment.

    Returns:
        str: HTML document containing payment details and audit history.
    """
    payment = repository().get_payment(payment_id)
    return render_template("detail.html", payment=payment)
