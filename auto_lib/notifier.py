import logging
import os
import subprocess

import requests

log = logging.getLogger(__name__)


def _macos_notify(title: str, message: str):
    safe_title = title.replace('"', '\\"')
    safe_message = message.replace('"', '\\"')
    try:
        subprocess.run(
            ["osascript", "-e", f'display notification "{safe_message}" with title "{safe_title}" sound name "Basso"'],
            timeout=5,
            capture_output=True,
        )
    except Exception as e:
        log.debug("macOS notification failed: %s", e)


def _slack_notify(title: str, message: str):
    webhook = os.environ.get("SLACK_WEBHOOK_URL")
    if not webhook:
        return
    try:
        requests.post(webhook, json={"text": f"*{title}*\n{message}"}, timeout=10)
    except Exception as e:
        log.debug("Slack notification failed: %s", e)


def notify_intervention_needed(title: str, message: str):
    """Send a notification that manual intervention is required."""
    log.warning("MANUAL INTERVENTION NEEDED: %s — %s", title, message)
    _macos_notify(f"Action needed: {title}", message)
    _slack_notify(f"Action needed: {title}", message)
