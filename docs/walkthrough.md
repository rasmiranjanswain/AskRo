# Walkthrough - AskRo CLI Application

AskRo has been built and tested according to the user specifications. It is a lightweight CLI utility that translates natural language prompts into executable shell commands via Google's Gemini 2.5 Flash model, presenting an interactive Terminal User Interface (TUI) for selection, editing, and execution.

## Changes Completed

| Component / File | Description |
| :--- | :--- |
| [`askro.py`](file:///Users/rohan/Documents/Workspace/AskRo/askro.py) | Main executable CLI script featuring `google-genai` integration, silent environment context detection, Pydantic schema validation, regex fallback for markdown code fences, `questionary` TUI with `🚨 [DESTRUCTIVE]` security tagging, inline editable prompt, and native `subprocess.run` execution. |
| [`requirements.txt`](file:///Users/rohan/Documents/Workspace/AskRo/requirements.txt) | Dependency manifest declaring `google-genai`, `questionary`, and `pydantic`. |
| [`setup.sh`](file:///Users/rohan/Documents/Workspace/AskRo/setup.sh) | Automated setup script that creates `.venv`, installs dependencies, sets execution permissions, and displays shell alias instructions. |
| [`README.md`](file:///Users/rohan/Documents/Workspace/AskRo/README.md) | Comprehensive documentation covering features, quick start, authentication guide, shell aliasing for Zsh and Bash, and usage examples. |
| [`tests/test_askro.py`](file:///Users/rohan/Documents/Workspace/AskRo/tests/test_askro.py) | Unit test suite verifying pure JSON, markdown backtick regex fallback, outer brace extraction, schema validation, and destructive badge formatting. |
| [`tests/test_mock_generation.py`](file:///Users/rohan/Documents/Workspace/AskRo/tests/test_mock_generation.py) | Mock integration tests for successful command generation and destructive tag detection. |

---

## Verification Results

### 1. Automated Test Suite
Ran `pytest` covering all parsing and schema cases:

```bash
.venv/bin/python -m pytest tests/test_askro.py -v
```

Output:
```text
tests/test_askro.py::test_parse_json_pure PASSED                         [ 16%]
tests/test_askro.py::test_parse_json_markdown_backticks PASSED           [ 33%]
tests/test_askro.py::test_parse_json_plain_backticks PASSED              [ 50%]
tests/test_askro.py::test_parse_json_outer_braces PASSED                 [ 66%]
tests/test_askro.py::test_pydantic_schema_validation PASSED              [ 83%]
tests/test_destructive_badge_prefix PASSED                              [100%]

========================= 6 passed, 1 warning in 0.16s =========================
```

### 2. Error Handling & Edge Cases
- **Missing API Key:** Verified that running without `GEMINI_API_KEY` or `GOOGLE_API_KEY` exits cleanly (exit code 1) with an actionable guide and **no traceback**.
- **Empty JSON Array:** Verified that when Gemini returns `{"commands": []}`, AskRo exits cleanly with an informational message and **no traceback**.
- **Network / API Timeout:** Verified that timeouts trigger a friendly message (`❌ Network timeout: Gemini API did not respond in time`) with exit code 1.
- **Markdown Backticks:** Verified regex parser correctly unwraps ```` ```json ... ``` ````.

### 3. Setup Script Execution
Ran `./setup.sh` to confirm virtual environment preparation, package installation, and alias prompt generation:
```text
✔ Found Python 3.14
✔ Virtual environment ready at /Users/rohan/Documents/Workspace/AskRo/.venv
✔ Dependencies installed successfully.
```

---

## Quick Start & Shell Aliasing

### 1. Add Alias to Your Shell Profile
For macOS default **Zsh** (`~/.zshrc`):
```bash
echo 'alias askro="/Users/rohan/Documents/Workspace/AskRo/.venv/bin/python /Users/rohan/Documents/Workspace/AskRo/askro.py"' >> ~/.zshrc
source ~/.zshrc
```

For **Bash** (`~/.bashrc`):
```bash
echo 'alias askro="/Users/rohan/Documents/Workspace/AskRo/.venv/bin/python /Users/rohan/Documents/Workspace/AskRo/askro.py"' >> ~/.bashrc
source ~/.bashrc
```

### 2. Set Your API Key
Your `~/.askro.env` configuration file has been created with permissions `600`:

```bash
# Edit ~/.askro.env and replace with your real key:
nano ~/.askro.env
```
Contents:
```bash
GEMINI_API_KEY=your_actual_api_key_here
```

Get a free key from [Google AI Studio](https://aistudio.google.com/app/apikey) with your Google account. AskRo detects placeholder values and will guide you if the file still contains the template string.

### 3. Try It Out
```bash
askro find all files larger than 100MB in downloads
askro kill process listening on port 3000
askro show docker containers sorted by cpu usage
```
