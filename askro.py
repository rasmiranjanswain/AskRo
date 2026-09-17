#!/usr/bin/env python3
"""
AskRo - Natural Language to Shell Command CLI Utility.
Translates human queries into executable shell commands via Gemini 2.5 Flash,
providing an interactive TUI for selection, risk review, editing, and native execution.
"""

import sys
import os
import re
import json
import warnings
import logging
import platform
import subprocess
from typing import List, Literal, Optional
from pydantic import BaseModel, Field

# Suppress internal SDK notices and function-calling warnings
logging.getLogger("google_genai").setLevel(logging.ERROR)
logging.getLogger("google.genai").setLevel(logging.ERROR)
warnings.filterwarnings("ignore")

# Graceful import check for dependencies
try:
    from google import genai
    from google.genai import types
except ImportError:
    print("❌ Error: Missing required package 'google-genai'.")
    print("Please install dependencies using: pip install -r requirements.txt")
    sys.exit(1)

try:
    import questionary
    from questionary import Style
except ImportError:
    print("❌ Error: Missing required package 'questionary'.")
    print("Please install dependencies using: pip install -r requirements.txt")
    sys.exit(1)


# ─── Pydantic Schema for Strict Output ───────────────────────────────────────
class CommandItem(BaseModel):
    command: str = Field(description="The executable shell command string")
    description: str = Field(description="Short description of what the command does")
    risk_level: Literal["LOW", "MEDIUM", "HIGH"] = Field(
        description="Risk level: LOW (read-only), MEDIUM (non-destructive change), HIGH (destructive/modifying)"
    )
    is_destructive: bool = Field(
        description="True if the command deletes files, kills processes, overwrites data, or changes system configuration"
    )


class CommandResponse(BaseModel):
    commands: List[CommandItem] = Field(description="List of 1 to 3 command suggestions")


# ─── Custom TUI Styling ──────────────────────────────────────────────────────
TUI_STYLE = Style(
    [
        ("qmark", "fg:#00bcd4 bold"),         # Question mark symbol
        ("question", "bold"),                 # Question text
        ("answer", "fg:#00e676 bold"),        # Selected answer
        ("pointer", "fg:#00bcd4 bold"),       # Pointer '»'
        ("highlighted", "fg:#00bcd4 bold"),   # Highlighted choice
        ("selected", "fg:#00e676"),           # Selected item
        ("instruction", "fg:#888888 italic"), # Hint text
    ]
)


def load_api_key() -> Optional[str]:
    """Retrieve Gemini API key from environment or local/user config files."""
    # 1. Environment variables
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if api_key and api_key.strip():
        return api_key.strip()

    # 2. Check ~/.askro.env or local .env
    candidates = [
        os.path.expanduser("~/.askro.env"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"),
    ]
    for filepath in candidates:
        if os.path.isfile(filepath):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            key, val = line.split("=", 1)
                            key = key.strip()
                            val = val.strip().strip("'\"")
                            if key in ("GEMINI_API_KEY", "GOOGLE_API_KEY") and val:
                                os.environ[key] = val
                                return val
            except Exception:
                pass

    return None


def get_genai_client() -> genai.Client:
    """Initialize Google GenAI SDK client with proper authentication."""
    api_key = load_api_key()

    # Detect placeholder strings
    if api_key and any(p in api_key.lower() for p in ("your-gemini-api-key", "your_api_key_here", "placeholder")):
        print("\n⚠️ Notice: GEMINI_API_KEY in ~/.askro.env is set to a placeholder.")
        print("Please edit ~/.askro.env and paste your actual Gemini API key:")
        print("  GEMINI_API_KEY=AIzaSy...")
        print("\nGet a free API key at: https://aistudio.google.com/app/apikey\n")
        sys.exit(1)

    if api_key:
        return genai.Client(api_key=api_key)

    # Check for Google Cloud project (Vertex AI fallback)
    gcp_project = os.environ.get("GOOGLE_CLOUD_PROJECT")
    if gcp_project:
        try:
            return genai.Client(vertexai=True, project=gcp_project)
        except Exception:
            pass

    # Attempt default initialization
    try:
        return genai.Client()
    except Exception:
        print("\n❌ Error: Google Gemini API key not found.\n")
        print("To authenticate AskRo, please set your GEMINI_API_KEY:")
        print("  export GEMINI_API_KEY='your_api_key_here'\n")
        print("You can get a free API key with your Google account at:")
        print("  👉 https://aistudio.google.com/app/apikey\n")
        print("Alternatively, you can create a ~/.askro.env file containing:")
        print("  GEMINI_API_KEY=your_api_key_here\n")
        sys.exit(1)


def parse_json_safely(raw_text: str) -> dict:
    """
    Parse JSON from the model response with robust regex fallback to strip
    markdown code blocks (```json ... ```) or find JSON object boundaries.
    """
    text = raw_text.strip()

    # 1. Direct JSON parse
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass

    # 2. Regex fallback for markdown backticks (```json ... ``` or ``` ... ```)
    code_block_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
    if code_block_match:
        extracted = code_block_match.group(1).strip()
        try:
            data = json.loads(extracted)
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass

    # 3. Boundary search for outermost { ... }
    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        snippet = text[first_brace : last_brace + 1]
        try:
            data = json.loads(snippet)
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass

    print("\n❌ Error: Unable to parse structured JSON from the model response.")
    print(f"Response preview:\n{text[:300]}")
    sys.exit(1)


def generate_commands(client: genai.Client, query: str) -> List[dict]:
    """
    Query Gemini 2.5 Flash with the user's request and system context,
    enforcing strict JSON output matching the CommandResponse schema.
    """
    # 1. Context: Silently grab platform.system() and os.environ.get("SHELL")
    system_os = platform.system()
    shell_env = os.environ.get("SHELL", "/bin/sh")
    shell_name = os.path.basename(shell_env)
    cwd = os.getcwd()

    system_instruction = (
        f"You are AskRo, an expert shell command assistant for {system_os} using {shell_name}.\n"
        f"Current working directory: {cwd}\n\n"
        "Your task: Translate natural language requests into 1 to 3 valid, executable shell commands.\n\n"
        "Rules:\n"
        f"1. Generate syntax strictly compatible with {shell_name} on {system_os}.\n"
        "2. Provide 1 to 3 command alternatives (e.g. standard command, concise option, or alternative tool).\n"
        "3. Evaluate risk accurately:\n"
        "   - 'is_destructive': true if the command removes files, kills processes, overwrites data, or changes system state.\n"
        "   - 'risk_level': 'LOW' for inspection/read-only commands, 'MEDIUM' for non-destructive mutations, 'HIGH' for destructive or irreversible actions.\n"
        "4. Output MUST conform strictly to the required JSON schema with no preamble or prose outside JSON."
    )

    prompt = (
        f"Generate shell command(s) for the following query:\n"
        f"Query: {query}\n"
        f"Operating System: {system_os}\n"
        f"Shell: {shell_name} ({shell_env})"
    )

    models_to_try = ["gemini-3.5-flash", "gemini-3.6-flash", "gemini-3.7-flash"]
    response = None
    last_error = None

    for model_name in models_to_try:
        try:
            config = types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                response_schema=CommandResponse,
                temperature=0.2,
            )

            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=config,
            )
            if response and response.text:
                break
        except Exception as e:
            last_error = e
            err_str = str(e)
            err_lower = err_str.lower()
            # If model is deprecated (404) or experiencing temporary high demand (503), try next model
            if any(k in err_str for k in ("404", "503", "UNAVAILABLE")) or "no longer available" in err_lower:
                continue
            # Auth or quota errors
            if "quota" in err_lower or "429" in err_str:
                print("\n❌ Gemini API rate limit or quota exceeded. Please wait a moment and retry.")
            elif "api_key" in err_lower or "unauthenticated" in err_lower or "401" in err_str or "403" in err_str:
                print(f"\n❌ Gemini API authentication failure: {err_str}")
                print("Please verify that your GEMINI_API_KEY is valid.")
            elif "timeout" in err_lower or "timed out" in err_lower:
                print("\n❌ Network timeout: Gemini API did not respond in time. Please try again.")
            else:
                print(f"\n❌ Gemini API error: {err_str}")
            sys.exit(1)

    if not response or not response.text:
        if last_error:
            print(f"\n❌ Gemini API error: {last_error}")
            sys.exit(1)
        print(f"\n❌ Empty response received from Gemini for query: '{query}'")
        sys.exit(1)

    raw_text = response.text or ""

    # Parse and validate with regex fallback
    data = parse_json_safely(raw_text)
    commands = data.get("commands", [])

    # Catch empty JSON arrays gracefully and exit with clean print statement
    if not commands or not isinstance(commands, list):
        print(f"\nℹ️  No executable commands generated for: \"{query}\"")
        print("Try rephrasing with additional context or details.")
        sys.exit(0)

    return commands


def main():
    """AskRo Main CLI Flow."""
    # Banner / Help flag
    if len(sys.argv) > 1 and sys.argv[1] in ("-h", "--help"):
        print("AskRo - Natural Language to Shell Command CLI")
        print("\nUsage:")
        print("  askro <natural language query>")
        print("  askro               (interactive prompt)")
        print("\nExamples:")
        print("  askro find files larger than 500MB")
        print("  askro kill process listening on port 8080")
        print("  askro show git branches sorted by last commit")
        sys.exit(0)

    # Query extraction: accept CLI arguments or prompt interactively
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:]).strip()
    else:
        try:
            query = questionary.text(
                "What command do you need?",
                style=TUI_STYLE,
                instruction="(Type in plain English, e.g., 'extract tar.gz archive')"
            ).ask()
        except KeyboardInterrupt:
            print("\nCancelled.")
            sys.exit(0)

        if not query or not query.strip():
            print("No query provided. Exiting.")
            sys.exit(0)

    # Initialize client & request suggestions
    client = get_genai_client()

    print(f"\n🔍 Consulting Gemini for: \"{query}\"...")
    commands = generate_commands(client, query)

    # Build TUI choices
    choices = []
    for cmd in commands:
        cmd_str = cmd.get("command", "").strip()
        desc = cmd.get("description", "").strip()
        risk = cmd.get("risk_level", "LOW").upper()
        is_destructive = bool(cmd.get("is_destructive", False))

        # Security: Prefix choice with 🚨 [DESTRUCTIVE] if is_destructive is true
        prefix = "🚨 [DESTRUCTIVE] " if is_destructive else ""
        risk_badge = f"[{risk}]"

        # Format readable title with command, risk level, and description
        if desc:
            display_title = f"{prefix}{risk_badge} {cmd_str}  — {desc}"
        else:
            display_title = f"{prefix}{risk_badge} {cmd_str}"

        choices.append(
            questionary.Choice(
                title=display_title,
                value=cmd_str,
            )
        )

    # Add cancel option
    choices.append(
        questionary.Choice(
            title="🚫 Cancel / Exit",
            value="__CANCEL__",
        )
    )

    # 4. Interactive TUI: Select command
    try:
        selected_command = questionary.select(
            "Select a command:",
            choices=choices,
            style=TUI_STYLE,
            use_arrow_keys=True,
            use_jk_keys=True,
        ).ask()
    except KeyboardInterrupt:
        print("\nExecution cancelled.")
        sys.exit(0)

    if not selected_command or selected_command == "__CANCEL__":
        print("Execution cancelled.")
        sys.exit(0)

    # 6. Editable Execution: Drop into questionary.text for inline editing
    try:
        final_command = questionary.text(
            "Edit command before executing:",
            default=selected_command,
            style=TUI_STYLE,
            instruction="(Press Enter to execute, Ctrl+C to cancel)"
        ).ask()
    except KeyboardInterrupt:
        print("\nExecution cancelled.")
        sys.exit(0)

    if not final_command or not final_command.strip():
        print("Execution cancelled.")
        sys.exit(0)

    final_command = final_command.strip()

    # 7. Execution: Run natively using subprocess.run(shell=True)
    print(f"\n🚀 Running: {final_command}\n" + "─" * 60)
    try:
        result = subprocess.run(final_command, shell=True)
        print("─" * 60)
        sys.exit(result.returncode)
    except KeyboardInterrupt:
        print("\n⚠️  Command execution interrupted by user.")
        sys.exit(130)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nAborted.")
        sys.exit(0)
