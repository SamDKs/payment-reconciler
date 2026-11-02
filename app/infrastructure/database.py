"""Open and close connections and manage atomic transactions."""

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from importlib.resources import files


class Database:
    """Manage the SQLite file without sharing connections between requests."""
    def __init__(self, path):
        """Initialize this component with its required dependencies.

        Args:
            path (str | Path): Path of the SQLite database file.

        Returns:
            None: Initialize the object without returning a value.
        """
        self.path = str(Path(path).resolve())  # Use an absolute path to consistently identify the database file.

    @contextmanager
    def connection(self):
        """Provide a connection and close it even if the operation fails.

        Args:
            None.

        Returns:
            contextlib.AbstractContextManager[sqlite3.Connection]: Context manager that provides a connection and handles cleanup.
        """
        connection = sqlite3.connect(self.path, timeout=5, isolation_level=None)  # Manage transaction boundaries explicitly.
        connection.row_factory = sqlite3.Row  # Allow access to columns by name: row["id"].
        connection.execute("PRAGMA foreign_keys = ON")  # Enforce foreign key relationships between tables.
        try:
            yield connection  # Yield the connection to the caller's with block.
        finally:
            connection.close()

    @contextmanager
    def transaction(self):
        """Commit all changes together or roll them back on error.

        Args:
            None.

        Returns:
            contextlib.AbstractContextManager[sqlite3.Connection]: Context manager that commits changes or rolls them back on error.
        """
        with self.connection() as connection:
            connection.execute("BEGIN IMMEDIATE")  # Acquire the write reservation before checking for duplicates.
            try:
                yield connection  # Yield the connection to the caller's with block.
                connection.commit()
            except Exception:
                connection.rollback()  # Also roll back invoice changes if the audit write fails.
                raise

    def initialize(self):
        """Create the data directory and execute the initial schema.

        Args:
            None.

        Returns:
            None: Prepare the database file and tables.
        """
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        schema = files("migrations").joinpath("001_initial.sql")  # Locate the SQL bundled with the installed package.
        with self.connection() as connection:
            connection.execute("PRAGMA journal_mode = WAL")  # Allow readers while a write is in progress.
            connection.executescript(schema.read_text())  # Execute statements from the initial SQL schema.
