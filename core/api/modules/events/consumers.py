"""Built-in subscribers. Each must cope with the same event twice (processed_events helps).

Email and webhooks come later; they register the same way, without touching booking code.
"""

import logging
from typing import Any

from modules.events.service import subscribe

logger = logging.getLogger("events.audit")


@subscribe("audit_log", ["*"])
def audit_log(event: dict[str, Any]) -> None:
    """Writes every event to the log. Placeholder for analytics and the email sender."""
    logger.info("event %s %s:%s", event["name"], event["subject"]["type"], event["subject"]["id"])
