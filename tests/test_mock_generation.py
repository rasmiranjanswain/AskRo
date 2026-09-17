#!/usr/bin/env python3
"""
Test mock generation flow for AskRo.
"""

import sys
import os
from unittest.mock import MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from askro import generate_commands


def test_generate_commands_success():
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = '{"commands": [{"command": "git status -s", "description": "Short git status", "risk_level": "LOW", "is_destructive": false}]}'
    mock_client.models.generate_content.return_value = mock_response

    commands = generate_commands(mock_client, "show brief git status")
    assert len(commands) == 1
    assert commands[0]["command"] == "git status -s"
    assert commands[0]["is_destructive"] is False


def test_generate_commands_destructive():
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = '```json\n{"commands": [{"command": "rm -rf node_modules", "description": "Delete node_modules directory", "risk_level": "HIGH", "is_destructive": true}]}\n```'
    mock_client.models.generate_content.return_value = mock_response

    commands = generate_commands(mock_client, "clean node modules")
    assert len(commands) == 1
    assert commands[0]["command"] == "rm -rf node_modules"
    assert commands[0]["is_destructive"] is True
    assert commands[0]["risk_level"] == "HIGH"


if __name__ == "__main__":
    test_generate_commands_success()
    test_generate_commands_destructive()
    print("Mock generation tests passed!")
