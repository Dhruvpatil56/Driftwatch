"""Application configuration — all values come from the environment / .env.

No secrets are hardcoded; AWS credentials are read by boto3 from the standard
environment variables, never from here.
"""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_REPO_ROOT = Path(__file__).resolve().parents[1]
_DEMO_DIR = _REPO_ROOT / "terraform-demo"


class Settings(BaseSettings):
    # Database (defaults target the docker-compose "postgres" service).
    database_url: str = "postgresql+psycopg2://driftwatch:driftwatch@postgres:5432/driftwatch"

    # AWS / detection
    aws_region: str = "ap-south-1"
    driftwatch_offline: bool = False

    # Detection inputs (overridable so tests can point at checked-in fixtures).
    hcl_path: str = str(_DEMO_DIR)
    tfstate_path: str = str(_DEMO_DIR / "terraform.tfstate")
    demo_actual_path: str = str(_DEMO_DIR / "actual-state.demo.json")

    # API
    cors_origins: str = "http://localhost:3000"
    scrape_interval_minutes: int = 15

    # Sprint 5 integrations. NOTE: the engine (scorer/explainer) and the Slack
    # notifier read these straight from os.environ so they stay decoupled and so
    # local test runs (where .env is not injected into the process environment)
    # default to "disabled". These fields exist for visibility/validation.
    opa_url: str = ""
    redis_url: str = ""
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    slack_webhook_url: str = ""
    github_token: str = ""
    github_repo: str = ""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
