"""
ai_router.py — shared hybrid AI router for all projects.
Routes: simple/medium → local Ollama (free), complex → Claude API (paid).
"""
import os
import logging
from typing import Literal

from auto_lib.local_ai import chat as local_chat, is_available, DEFAULT_CODE_MODEL, DEFAULT_FAST_MODEL

Complexity = Literal["simple", "medium", "complex"]


def route(prompt: str, complexity: Complexity = "simple", system: str = None,
          force_local: bool = False, force_cloud: bool = False) -> str:
    local_up = is_available()
    use_local = not force_cloud and (force_local or complexity in ("simple", "medium")) and local_up
    if use_local:
        model = DEFAULT_FAST_MODEL if complexity == "simple" else DEFAULT_CODE_MODEL
        logging.debug("[ai_router] LOCAL %s", model)
        return local_chat(prompt, model=model, system=system)
    if not local_up and not force_cloud:
        logging.warning("[ai_router] Ollama unavailable, falling back to Claude API")
    return _claude(prompt, system=system)


def _resolve_anthropic_key() -> str | None:
    """Env first, then macOS keychain (`security find-generic-password
    -s anthropic-api-key`). Avoids plaintext keys in .env / LaunchAgent plists."""
    k = os.environ.get("ANTHROPIC_API_KEY")
    if k:
        return k
    import subprocess
    try:
        res = subprocess.run(
            ["security", "find-generic-password", "-s", "anthropic-api-key", "-w"],
            capture_output=True, text=True, timeout=5, check=False,
        )
        tok = res.stdout.strip()
        if res.returncode == 0 and tok.startswith(("sk-ant-", "sk-")):
            return tok
    except (OSError, subprocess.SubprocessError) as e:
        logging.warning("[ai_router] keychain lookup failed: %s", e)
    return None


def _claude(prompt: str, system: str = None) -> str:
    import anthropic
    key = _resolve_anthropic_key()
    if not key:
        raise RuntimeError(
            "Anthropic credential not found. Set the env var or store it in "
            "macOS keychain (service name matching the lookup in "
            "_resolve_anthropic_key above)."
        )
    client = anthropic.Anthropic(api_key=key)
    kwargs = {
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 1024,
        "messages": [{"role": "user", "content": prompt}],
    }
    if system:
        kwargs["system"] = system
    return client.messages.create(**kwargs).content[0].text
