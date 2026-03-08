"""Wispr Flow integration client for MortgageFintechOS.

Handles webhook validation and processing of voice-to-text
transcriptions from Wispr Flow into structured notes for agent dispatch.
"""

import hashlib
import hmac
from datetime import datetime, timezone
from typing import Any

import structlog

logger = structlog.get_logger()

# Keywords that help route notes to the right agent
ROUTING_KEYWORDS = {
    "DIEGO": ["pipeline", "loan status", "stage", "priority", "triage", "application", "processing", "underwriting", "closing", "funding"],
    "MARTIN": ["document", "w-2", "paystub", "bank statement", "tax return", "appraisal", "title", "insurance", "classify", "audit"],
    "NOVA": ["income", "dti", "debt to income", "salary", "wage", "self-employed", "schedule c", "collections"],
    "JARVIS": ["condition", "loe", "letter of explanation", "prior to", "compliance", "cleared", "waived"],
    "ATLAS": ["api", "endpoint", "feature", "component", "scaffold", "migration", "build"],
    "CIPHER": ["security", "vulnerability", "owasp", "scan", "compliance", "encryption", "cve"],
    "FORGE": ["deploy", "rollback", "ci/cd", "pipeline", "secrets", "rotation"],
    "NEXUS": ["pull request", "pr review", "code quality", "test", "refactor", "tech debt"],
    "STORM": ["etl", "data", "hmda", "uldd", "report", "query", "export"],
}


class WisprClient:
    """Processes Wispr Flow voice-to-text webhooks for agent routing."""

    def __init__(self, webhook_secret: str = ""):
        self._secret = webhook_secret
        self._log = logger.bind(component="wispr")
        self._notes_received: int = 0
        self._last_note_at: datetime | None = None

    def validate_webhook(self, headers: dict[str, str], body: bytes) -> bool:
        """Validate webhook signature if secret is configured."""
        if not self._secret:
            return True  # No secret = accept all (dev mode)

        signature = headers.get("X-Wispr-Signature", "")
        if not signature:
            self._log.warning("wispr_missing_signature")
            return False

        expected = hmac.new(
            self._secret.encode(), body, hashlib.sha256
        ).hexdigest()

        valid = hmac.compare_digest(signature, expected)
        if not valid:
            self._log.warning("wispr_invalid_signature")
        return valid

    def process_note(self, note_text: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        """Parse a voice transcription into a structured note with routing info."""
        self._notes_received += 1
        self._last_note_at = datetime.now(timezone.utc)
        meta = metadata or {}

        # Determine which agent should handle this note
        text_lower = note_text.lower()
        scores: dict[str, int] = {}
        for agent, keywords in ROUTING_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            if score > 0:
                scores[agent] = score

        target_agent = max(scores, key=scores.get) if scores else "MARTIN"
        confidence = max(scores.values()) / 3.0 if scores else 0.3
        confidence = min(confidence, 1.0)

        note = {
            "text": note_text,
            "timestamp": self._last_note_at.isoformat(),
            "source": "wispr_flow",
            "speaker": meta.get("speaker", "unknown"),
            "duration_seconds": meta.get("duration", 0),
            "target_agent": target_agent,
            "routing_confidence": round(confidence, 2),
            "all_scores": scores,
        }

        self._log.info(
            "wispr_note_processed",
            target=target_agent,
            confidence=round(confidence, 2),
            length=len(note_text),
        )
        return note

    def get_status(self) -> dict[str, Any]:
        """Return Wispr integration status."""
        return {
            "configured": bool(self._secret),
            "notes_received": self._notes_received,
            "last_note_at": self._last_note_at.isoformat() if self._last_note_at else None,
        }
