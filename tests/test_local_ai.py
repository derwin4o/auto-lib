import pytest
from unittest.mock import patch, MagicMock


def test_is_available_true():
    with patch("auto_lib.local_ai.requests.get") as mock_get:
        mock_get.return_value.status_code = 200
        from auto_lib.local_ai import is_available
        assert is_available() is True


def test_is_available_false_on_error():
    with patch("auto_lib.local_ai.requests.get", side_effect=Exception("conn refused")):
        from auto_lib.local_ai import is_available
        assert is_available() is False


def test_chat_returns_content():
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "message": {"content": "hello"},
        "prompt_eval_count": 10,
        "eval_count": 5,
        "total_duration": 500_000_000,
    }
    mock_resp.raise_for_status = MagicMock()
    with patch("auto_lib.local_ai.requests.post", return_value=mock_resp):
        from auto_lib.local_ai import chat
        result = chat("say hello", model="llama3.2:3b")
    assert result == "hello"


def test_chat_with_system_prompt():
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "message": {"content": "response"},
        "prompt_eval_count": 5,
        "eval_count": 3,
        "total_duration": 100_000_000,
    }
    mock_resp.raise_for_status = MagicMock()
    with patch("auto_lib.local_ai.requests.post", return_value=mock_resp) as mock_post:
        from auto_lib.local_ai import chat
        chat("prompt", system="you are helpful")
    call_body = mock_post.call_args[1]["json"]
    assert call_body["messages"][0]["role"] == "system"
    assert call_body["messages"][0]["content"] == "you are helpful"


def test_usage_summary_returns_dict(tmp_path, monkeypatch):
    monkeypatch.setattr("auto_lib.local_ai._DB_PATH", tmp_path / "usage.db")
    from auto_lib.local_ai import usage_summary
    result = usage_summary(days=7)
    assert isinstance(result, dict)
