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

    # Notion (API v2025-09-03)
    notion_api_token: str = field(
        default_factory=lambda: os.getenv("NOTION_API_TOKEN", "")
    )
    notion_database_id: str = field(
        default_factory=lambda: os.getenv("NOTION_DATABASE_ID", "")
    )
    notion_data_source_id: str = field(
        default_factory=lambda: os.getenv("NOTION_DATA_SOURCE_ID", "")
    )

    # Wispr Flow
    wispr_webhook_secret: str = field(
        default_factory=lambda: os.getenv("WISPR_WEBHOOK_SECRET", "")
    )

    # Google Drive
    google_drive_folder_id: str = field(
        default_factory=lambda: os.getenv("GOOGLE_DRIVE_FOLDER_ID", "")
    )
    google_service_account_json: str = field(
        default_factory=lambda: os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "")
    )

    # LLM Router
    openai_api_key: str = field(
        default_factory=lambda: os.getenv("OPENAI_API_KEY", "")
    )
    anthropic_api_key: str = field(
        default_factory=lambda: os.getenv("ANTHROPIC_API_KEY", "")
    )
    openrouter_api_key: str = field(
        default_factory=lambda: os.getenv("OPENROUTER_API_KEY", "")
    )
    default_llm_provider: str = field(
        default_factory=lambda: os.getenv("DEFAULT_LLM_PROVIDER", "openrouter")
    )
    default_llm_model: str = field(
        default_factory=lambda: os.getenv("DEFAULT_LLM_MODEL", "anthropic/claude-sonnet-4-6")
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
    notion_sync_hour: int = 7
    notion_sync_minute: int = 30
    drive_import_hour: int = 5
    drive_import_minute: int = 30
    security_scan_hour: int = 3
    security_scan_minute: int = 0

    # Health monitoring thresholds
    heartbeat_timeout_seconds: int = 60
    queue_backlog_threshold: int = 50
    error_rate_threshold: float = 0.10
    error_rate_window_seconds: int = 300

    # Dashboard
    dashboard_port: int = field(
        default_factory=lambda: int(os.getenv("DASHBOARD_PORT", "8080"))
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
