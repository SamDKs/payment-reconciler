"""Local configuration and optional environment settings."""

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def settings():
    """Read optional environment variables and provide defaults.

    Args:
        None.

    Returns:
        dict: Database path and HTTP request body size limit.
    """
    return {
        "DATABASE": os.environ.get("RECONCILER_DATABASE", str(ROOT / "instance" / "reconciler.sqlite3")),
        "MAX_CONTENT_LENGTH": 16 * 1024,  # Limit each HTTP request body to 16 KB.
    }
