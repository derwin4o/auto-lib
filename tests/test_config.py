import json
import pytest
from pathlib import Path
from auto_lib.config import load_config, RepoConfig, Config


@pytest.fixture
def config_file(tmp_path, monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "test_token")
    cfg = {
        "repos": [{"owner": "acme", "name": "myrepo", "local_path": "/tmp/myrepo"}],
        "labels": {"easy": ["easy"], "hard": ["hard"]},
        "models": {"executor_model": "claude-haiku-4-5-20251001",
                   "chutes_executor_model": "chutesai/Mistral-Small-3.2-24B-Instruct-2506",
                   "planner_model": "claude-haiku-4-5-20251001",
                   "architect_model": "claude-sonnet-4-6"},
        "worktree_base": "/tmp/worktrees",
        "max_concurrent_per_repo": 1,
        "max_concurrent_easy_per_repo": 2,
        "executor_timeout_seconds": 600,
        "use_local_llm": True,
    }
    p = tmp_path / "config.json"
    p.write_text(json.dumps(cfg))
    return p


def test_load_config_returns_config(config_file):
    cfg = load_config(config_file)
    assert isinstance(cfg, Config)
    assert len(cfg.repos) == 1
    assert cfg.repos[0].name == "myrepo"
    assert cfg.github_token == "test_token"


def test_load_config_fails_without_github_token(config_file, monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    with pytest.raises(ValueError, match="GITHUB_TOKEN"):
        load_config(config_file)


def test_repo_config_defaults_merge_strategy():
    r = RepoConfig(owner="a", name="b", local_path="/tmp")
    assert r.merge_strategy == "pr"


def test_load_config_invalid_state_store(config_file, monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "tok")
    import json
    raw = json.loads(config_file.read_text())
    raw["state_store"] = {"type": "invalid"}
    config_file.write_text(json.dumps(raw))
    with pytest.raises(ValueError, match="Invalid state_store type"):
        load_config(config_file)
