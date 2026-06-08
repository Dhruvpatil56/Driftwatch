"""Block until the configured database accepts connections (used by containers
before running migrations).

Intentionally depends on nothing but ``DATABASE_URL`` from the environment, so
it works no matter what ``sys.path`` looks like inside the container.
"""

from __future__ import annotations

import os
import sys
import time

from sqlalchemy import create_engine, text

RETRIES = 60
DELAY_SECONDS = 2


def main() -> int:
    url = os.environ.get("DATABASE_URL")
    if not url:
        print("DATABASE_URL is not set; cannot wait for database")
        return 1

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
