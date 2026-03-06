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

    # Scheduler defaults — Mortgage Operations
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

    # Notifications
    slack_webhook_url: str = field(
        default_factory=lambda: os.getenv("SLACK_WEBHOOK_URL", "")
    )
    discord_webhook_url: str = field(
        default_factory=lambda: os.getenv("DISCORD_WEBHOOK_URL", "")
    )

    # LLM Integration — Free models for agent intelligence
    # Primary: Groq (free, fast inference for Llama 3.3 70B)
    # Secondary: Google Gemini 2.0 Flash (free tier, great for code)
    # Tertiary: Together AI (free credits, Llama 3.1 70B)
    llm_provider: str = field(
        default_factory=lambda: os.getenv("LLM_PROVIDER", "groq")
    )
    groq_api_key: str = field(
        default_factory=lambda: os.getenv("GROQ_API_KEY", "")
    )
    groq_model: str = field(
        default_factory=lambda: os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    )
    together_api_key: str = field(
        default_factory=lambda: os.getenv("TOGETHER_API_KEY", "")
    )
    together_model: str = field(
        default_factory=lambda: os.getenv("TOGETHER_MODEL", "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo")
    )
    google_api_key: str = field(
        default_factory=lambda: os.getenv("GOOGLE_API_KEY", "")
    )
    google_model: str = field(
        default_factory=lambda: os.getenv("GOOGLE_MODEL", "gemini-2.0-flash")
    )

    # GitHub Webhook Secret
    webhook_secret: str = field(
        default_factory=lambda: os.getenv("WEBHOOK_SECRET", "")
    )

    # Telegram Bot
    telegram_bot_token: str = field(
        default_factory=lambda: os.getenv("TELEGRAM_BOT_TOKEN", "")
    )
    telegram_webhook_secret: str = field(
        default_factory=lambda: os.getenv("TELEGRAM_WEBHOOK_SECRET", "")
    )

    # X.com (Twitter)
    x_api_key: str = field(
        default_factory=lambda: os.getenv("X_API_KEY", "")
    )
    x_api_secret: str = field(
        default_factory=lambda: os.getenv("X_API_SECRET", "")
    )
    x_access_token: str = field(
        default_factory=lambda: os.getenv("X_ACCESS_TOKEN", "")
    )
    x_access_secret: str = field(
        default_factory=lambda: os.getenv("X_ACCESS_SECRET", "")
    )
