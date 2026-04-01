import pytest
from unittest.mock import MagicMock, patch
from auto_lib.github_client import GitHubClient


@pytest.fixture
def gh():
    return GitHubClient(owner="acme", repo="myrepo", token="tok123")


def test_get_labeled_issues_filters_wip(gh):
    mock_resp = MagicMock()
    mock_resp.json.return_value = [
        {"number": 1, "title": "Fix bug", "labels": [{"name": "easy"}]},
        {"number": 2, "title": "WIP task", "labels": [{"name": "wip"}, {"name": "easy"}]},
        {"number": 3, "title": "PR", "labels": [], "pull_request": {}},
    ]
    mock_resp.raise_for_status = MagicMock()
    with patch.object(gh._session, "get", return_value=mock_resp):
        result = gh.get_labeled_issues(["easy"])
    assert len(result) == 1
    assert result[0]["number"] == 1


def test_get_issue_returns_normalized(gh):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "number": 42,
        "title": "Fix login",
        "body": "Detailed description",
        "labels": [{"name": "easy"}],
    }
    mock_resp.raise_for_status = MagicMock()
    with patch.object(gh._session, "get", return_value=mock_resp):
        result = gh.get_issue(42)
    assert result == {
        "number": 42,
        "title": "Fix login",
        "body": "Detailed description",
        "labels": [{"name": "easy"}],
    }


def test_add_label_calls_correct_endpoint(gh):
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    with patch.object(gh._session, "post", return_value=mock_resp) as mock_post:
        gh.add_label(7, "wip")
    mock_post.assert_called_once()
    url = mock_post.call_args[0][0]
    assert "/issues/7/labels" in url
    assert mock_post.call_args[1]["json"] == {"labels": ["wip"]}


def test_remove_label_ignores_404(gh):
    mock_resp = MagicMock()
    mock_resp.status_code = 404
    with patch.object(gh._session, "delete", return_value=mock_resp):
        gh.remove_label(7, "wip")  # should not raise


def test_post_comment(gh):
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    with patch.object(gh._session, "post", return_value=mock_resp) as mock_post:
        gh.post_comment(5, "hello")
    url = mock_post.call_args[0][0]
    assert "/issues/5/comments" in url
