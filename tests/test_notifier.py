import pytest
from unittest.mock import patch, MagicMock


def test_notify_calls_macos_and_slack():
    with patch("auto_lib.notifier._macos_notify") as mock_mac, \
         patch("auto_lib.notifier._slack_notify") as mock_slack:
        from auto_lib.notifier import notify_intervention_needed
        notify_intervention_needed("Test title", "Test message")
    mock_mac.assert_called_once_with("Action needed: Test title", "Test message")
    mock_slack.assert_called_once_with("Action needed: Test title", "Test message")


def test_macos_notify_does_not_raise_on_osascript_failure():
    with patch("auto_lib.notifier.subprocess.run", side_effect=Exception("osascript not found")):
        from auto_lib.notifier import _macos_notify
        _macos_notify("title", "message")  # should not raise


def test_slack_notify_skips_when_no_webhook(monkeypatch):
    monkeypatch.delenv("SLACK_WEBHOOK_URL", raising=False)
    from auto_lib.notifier import _slack_notify
    _slack_notify("title", "message")  # should not raise, no requests call made


def test_slack_notify_posts_when_webhook_set(monkeypatch):
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.slack.com/test")
    with patch("auto_lib.notifier.requests.post") as mock_post:
        mock_post.return_value.ok = True
        from auto_lib.notifier import _slack_notify
        _slack_notify("title", "message")
    mock_post.assert_called_once()
