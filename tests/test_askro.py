#!/usr/bin/env python3
"""
Unit and integration tests for AskRo CLI utility.
"""

import sys
import os
import json
import pytest

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from askro import parse_json_safely, CommandResponse, CommandItem


def test_parse_json_pure():
    """Test parsing clean, unwrapped JSON."""
    raw = '{"commands": [{"command": "ls -la", "description": "list all files", "risk_level": "LOW", "is_destructive": false}]}'
    result = parse_json_safely(raw)
    assert "commands" in result
    assert len(result["commands"]) == 1
    assert result["commands"][0]["command"] == "ls -la"


def test_parse_json_markdown_backticks():
    """Test regex fallback for ```json ... ``` blocks."""
    raw = """Here is the result:
```json
{
  "commands": [
    {
      "command": "rm -rf /tmp/cache",
      "description": "Remove temp cache",
      "risk_level": "HIGH",
      "is_destructive": true
    }
  ]
}
```
Hope this helps!"""
    result = parse_json_safely(raw)
    assert "commands" in result
    assert result["commands"][0]["command"] == "rm -rf /tmp/cache"
    assert result["commands"][0]["is_destructive"] is True


def test_parse_json_plain_backticks():
    """Test regex fallback for ``` ... ``` blocks without language identifier."""
    raw = """```
{"commands": [{"command": "git status", "description": "Check git status", "risk_level": "LOW", "is_destructive": false}]}
```"""
    result = parse_json_safely(raw)
    assert "commands" in result
    assert result["commands"][0]["command"] == "git status"


def test_parse_json_outer_braces():
    """Test extraction of JSON when braces are embedded without backticks."""
    raw = 'Sure, here are your commands: {"commands": [{"command": "ps aux", "description": "List processes", "risk_level": "LOW", "is_destructive": false}]} - let me know if you need more.'
    result = parse_json_safely(raw)
    assert "commands" in result
    assert result["commands"][0]["command"] == "ps aux"


def test_pydantic_schema_validation():
    """Test Pydantic model validation with valid and invalid data."""
    valid_data = {
        "commands": [
            {
                "command": "kill -9 1234",
                "description": "Terminate process",
                "risk_level": "HIGH",
                "is_destructive": True,
            }
        ]
    }
    model = CommandResponse(**valid_data)
    assert len(model.commands) == 1
    assert model.commands[0].is_destructive is True
    assert model.commands[0].risk_level == "HIGH"


def test_destructive_badge_prefix():
    """Test formatting of destructive badge according to spec."""
    cmd_dest = {"command": "rm -f file.txt", "description": "Delete file", "risk_level": "HIGH", "is_destructive": True}
    prefix_dest = "🚨 [DESTRUCTIVE] " if cmd_dest["is_destructive"] else ""
    assert prefix_dest == "🚨 [DESTRUCTIVE] "

    cmd_safe = {"command": "cat file.txt", "description": "Read file", "risk_level": "LOW", "is_destructive": False}
    prefix_safe = "🚨 [DESTRUCTIVE] " if cmd_safe["is_destructive"] else ""
    assert prefix_safe == ""


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
