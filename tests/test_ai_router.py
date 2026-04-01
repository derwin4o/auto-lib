import pytest
from unittest.mock import patch, MagicMock


def test_route_uses_local_for_simple():
    with patch("auto_lib.ai_router.is_available", return_value=True), \
         patch("auto_lib.ai_router.local_chat", return_value="local answer") as mock_local:
        from auto_lib.ai_router import route
        result = route("hello", complexity="simple")
    assert result == "local answer"
    mock_local.assert_called_once()


def test_route_uses_local_for_medium():
    with patch("auto_lib.ai_router.is_available", return_value=True), \
         patch("auto_lib.ai_router.local_chat", return_value="medium answer") as mock_local:
        from auto_lib.ai_router import route
        result = route("hello", complexity="medium")
    assert result == "medium answer"
    mock_local.assert_called_once()


def test_route_falls_back_to_claude_when_ollama_down():
    with patch("auto_lib.ai_router.is_available", return_value=False), \
         patch("auto_lib.ai_router._claude", return_value="cloud answer") as mock_claude:
        from auto_lib.ai_router import route
        result = route("hello", complexity="simple")
    assert result == "cloud answer"
    mock_claude.assert_called_once()


def test_route_force_cloud_skips_local():
    with patch("auto_lib.ai_router.is_available", return_value=True), \
         patch("auto_lib.ai_router._claude", return_value="cloud answer") as mock_claude:
        from auto_lib.ai_router import route
        result = route("hello", force_cloud=True)
    assert result == "cloud answer"
    mock_claude.assert_called_once()


def test_route_complex_goes_to_claude():
    with patch("auto_lib.ai_router.is_available", return_value=True), \
         patch("auto_lib.ai_router._claude", return_value="complex answer") as mock_claude:
        from auto_lib.ai_router import route
        result = route("hello", complexity="complex")
    assert result == "complex answer"
    mock_claude.assert_called_once()
