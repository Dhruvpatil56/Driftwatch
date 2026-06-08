"""APScheduler-based drift scraper.

Runs ``scan_and_persist`` once at boot and then every
``SCRAPE_INTERVAL_MINUTES`` minutes (default 15). Shares the exact detection +
persistence logic used by the API.
"""

from __future__ import annotations

import logging

from apscheduler.schedulers.blocking import BlockingScheduler

from api import services
from api.config import settings
from api.database import Base, SessionLocal, engine

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("driftwatch.scraper")


def run_scan() -> None:
    db = SessionLocal()
    try:
        events = services.scan_and_persist(db)
        logger.info("scan complete: %d active drift event(s)", len(events))
    except Exception as exc:  # noqa: BLE001
        logger.warning("scan failed: %s", exc)
    finally:
        db.close()


def main() -> None:
    Base.metadata.create_all(bind=engine)
    run_scan()  # run immediately on boot

    scheduler = BlockingScheduler(timezone="UTC")
    scheduler.add_job(
        run_scan,
        "interval",
        minutes=settings.scrape_interval_minutes,
        id="drift_scan",
    )
    logger.info("scraper started; interval = %d min", settings.scrape_interval_minutes)
    scheduler.start()


if __name__ == "__main__":
    main()
