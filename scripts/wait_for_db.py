"""Block until the configured database accepts connections (used by containers
before running migrations)."""

from __future__ import annotations

import sys
import time

from sqlalchemy import create_engine, text

from api.config import settings

RETRIES = 60
DELAY_SECONDS = 2


def main() -> int:
    url = settings.database_url
    for attempt in range(1, RETRIES + 1):
        try:
            engine = create_engine(url)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            print(f"database ready after {attempt} attempt(s)")
            return 0
        except Exception as exc:  # noqa: BLE001
            print(f"[{attempt}/{RETRIES}] waiting for database: {exc}")
            time.sleep(DELAY_SECONDS)
    print("database did not become ready in time")
    return 1


if __name__ == "__main__":
    sys.exit(main())
