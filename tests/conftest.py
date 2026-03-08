import os
from pathlib import Path


def pytest_configure() -> None:
    # Ensure tests never share the developer's local DB file and never leak state
    # across runs. This runs before test modules are imported.
    os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///./chatbot_test.db")
    Path("chatbot_test.db").unlink(missing_ok=True)
