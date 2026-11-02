"""Application errors translated into HTTP responses by the routes."""

class ValidationError(ValueError):
    """Invalid input."""


class ConflictError(Exception):
    """Existing identifier with incompatible data."""


class NotFoundError(Exception):
    """Requested record does not exist."""
