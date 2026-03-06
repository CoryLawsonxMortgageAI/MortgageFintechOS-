"""Central configuration for MortgageFintechOS."""

import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    database_url: str = field(
        default_factory=lambda: os.getenv("DATABASE_URL", "postgresql://localhost:5432/mortgageos")
    )
    redis_url: str = field(
        default_factory=lambda: os.getenv("REDIS_URL", "redis://localhost:6379")
    )
    github_token: str = field(
        default_factory=lambda: os.getenv("GITHUB_TOKEN", "")
    )
    github_repo: str = field(
        default_factory=lambda: os.getenv("GITHUB_REPO", "CoryLawsonxMortgageAI/MortgageFintechOS-")
    )
    log_level: str = field(
        default_factory=lambda: os.getenv("LOG_LEVEL", "INFO")
    )
    agent_retry_count: int = field(
        default_factory=lambda: int(os.getenv("AGENT_RETRY_COUNT", "3"))
    )
    agent_heartbeat_interval: int = field(
        default_factory=lambda: int(os.getenv("AGENT_HEARTBEAT_INTERVAL", "30"))
    )
    encryption_key: str = field(
        default_factory=lambda: os.getenv("ENCRYPTION_KEY", "")
    )

    # Scheduler defaults
    document_audit_hour: int = 6
    document_audit_minute: int = 0
    income_recalc_hour: int = 6
    income_recalc_minute: int = 30
    pipeline_check_hour: int = 7
    pipeline_check_minute: int = 0
    queue_check_interval_minutes: int = 60
    weekly_report_day: int = 0  # Monday

    # Health monitoring thresholds
    heartbeat_timeout_seconds: int = 60
    queue_backlog_threshold: int = 50
    error_rate_threshold: float = 0.10
    error_rate_window_seconds: int = 300

    # Dashboard
    dashboard_port: int = field(
        default_factory=lambda: int(os.getenv("PORT", os.getenv("DASHBOARD_PORT", "8080")))
    )
    dashboard_host: str = field(
        default_factory=lambda: os.getenv("DASHBOARD_HOST", "0.0.0.0")
    )

    # Persistence
    data_dir: str = field(
        default_factory=lambda: os.getenv("DATA_DIR", "data")
    )

    # Watchdog
    watchdog_interval: int = 30
    watchdog_max_crashes: int = 5
