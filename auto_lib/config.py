import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

import yaml

ALLOWED_STATE_STORE_TYPES = ["file", "sqlite", "redis"]


@dataclass
class RepoConfig:
    owner: str
    name: str
    local_path: str
    merge_strategy: str = "pr"  # "pr" or "direct"


@dataclass
class LabelConfig:
    easy: List[str]
    hard: List[str]
    architecture: List[str] = field(default_factory=list)


@dataclass
class ModelConfig:
    executor_model: str = "claude-haiku-4-5-20251001"
    chutes_executor_model: str = "chutesai/Mistral-Small-3.2-24B-Instruct-2506"
    planner_model: str = "claude-haiku-4-5-20251001"
    architect_model: str = "claude-sonnet-4-6"


@dataclass
class StateStoreConfig:
    type: str = "file"

    def __post_init__(self):
        if self.type not in ALLOWED_STATE_STORE_TYPES:
            raise ValueError(
                f"Invalid state_store type: '{self.type}'. "
                f"Allowed values: {', '.join(ALLOWED_STATE_STORE_TYPES)}"
            )


@dataclass
class Config:
    repos: List[RepoConfig]
    labels: LabelConfig
    models: ModelConfig
    worktree_base: str
    max_concurrent_per_repo: int
    max_concurrent_easy_per_repo: int
    executor_timeout_seconds: int
    github_token: str = field(repr=False, default="")
    use_local_llm: bool = True
    state_store: StateStoreConfig = field(default_factory=lambda: StateStoreConfig(type="file"))


def load_config(config_path: Path = None) -> Config:
    """Load config from JSON or YAML. Caller is responsible for loading .env before calling."""
    if config_path is None:
        config_path = Path("config.json")
    config_path = Path(config_path)

    with open(config_path) as f:
        raw = yaml.safe_load(f) if config_path.suffix.lower() in (".yaml", ".yml") else json.load(f)

    if not os.environ.get("GITHUB_TOKEN"):
        raise ValueError("Missing required environment variable: GITHUB_TOKEN")

    state_store = StateStoreConfig(**raw.get("state_store", {"type": "file"}))

    return Config(
        repos=[RepoConfig(**r) for r in raw["repos"]],
        labels=LabelConfig(**raw["labels"]),
        models=ModelConfig(**raw["models"]),
        worktree_base=raw["worktree_base"],
        max_concurrent_per_repo=raw["max_concurrent_per_repo"],
        max_concurrent_easy_per_repo=raw.get("max_concurrent_easy_per_repo", raw["max_concurrent_per_repo"]),
        executor_timeout_seconds=raw.get("executor_timeout_seconds", 600),
        state_store=state_store,
        github_token=os.environ["GITHUB_TOKEN"],
        use_local_llm=raw.get("use_local_llm", True),
    )
