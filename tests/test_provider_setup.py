#!/usr/bin/env python3
"""
Tests for provider selection, API key prompting, and config persistence.
"""

import os
import sys
import stat
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import askro


@pytest.fixture(autouse=True)
def isolated_env(tmp_path, monkeypatch):
    """Point config at a temp file and hide any real keys/env files."""
    monkeypatch.setenv("ASKRO_CONFIG", str(tmp_path / "askro" / "config.json"))
    monkeypatch.setenv("HOME", str(tmp_path))
    for var in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
        monkeypatch.delenv(var, raising=False)
    # Ignore the project's local .env during tests
    real_isfile = os.path.isfile
    monkeypatch.setattr(askro.os.path, "isfile", lambda p: False if p.endswith(".env") else real_isfile(p))


def test_first_run_prompts_provider_and_key_then_saves():
    with patch.object(askro, "select_provider", return_value="gemini") as sel, \
         patch.object(askro, "prompt_api_key", return_value="AIzaTestKey123") as key:
        provider, api_key = askro.setup_provider()

    assert (provider, api_key) == ("gemini", "AIzaTestKey123")
    sel.assert_called_once()
    key.assert_called_once_with("gemini")

    saved = askro.load_config()
    assert saved["provider"] == "gemini"
    assert saved["api_keys"]["gemini"] == "AIzaTestKey123"
    mode = stat.S_IMODE(os.stat(askro.config_path()).st_mode)
    assert mode == 0o600


def test_second_run_uses_saved_config_without_prompting():
    askro.save_config({"provider": "gemini", "api_keys": {"gemini": "AIzaSaved"}})
    with patch.object(askro, "select_provider") as sel, patch.object(askro, "prompt_api_key") as key:
        provider, api_key = askro.setup_provider()

    assert (provider, api_key) == ("gemini", "AIzaSaved")
    sel.assert_not_called()
    key.assert_not_called()


def test_reconfigure_prompts_again_and_overwrites():
    askro.save_config({"provider": "gemini", "api_keys": {"gemini": "AIzaOld"}})
    with patch.object(askro, "select_provider", return_value="gemini"), \
         patch.object(askro, "prompt_api_key", return_value="AIzaNew"):
        _, api_key = askro.setup_provider(reconfigure=True)

    assert api_key == "AIzaNew"
    assert askro.load_config()["api_keys"]["gemini"] == "AIzaNew"


def test_env_key_skips_key_prompt(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "AIzaFromEnv")
    with patch.object(askro, "select_provider", return_value="gemini"), \
         patch.object(askro, "prompt_api_key") as key:
        _, api_key = askro.setup_provider()

    assert api_key == "AIzaFromEnv"
    key.assert_not_called()


def test_placeholder_values_are_rejected(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "your-gemini-api-key")
    assert askro.env_api_key("gemini") is None
    assert askro.is_placeholder("[GCP_API_KEY]")
    assert not askro.is_placeholder("AIzaRealLookingKey")


def test_corrupt_config_is_treated_as_missing():
    path = askro.config_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write("{not json")
    assert askro.load_config() == {}
