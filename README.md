# AskRo ⚡

> **Natural Language to Executable Shell Commands with Gemini 2.5 Flash & Questionary TUI.**

AskRo is a lightweight command-line utility for macOS and Linux that translates human requests into verified, context-aware shell commands. It features an interactive Terminal User Interface (TUI) allowing you to inspect command risk levels, edit commands inline before execution, and run them natively.

---

## Features

- 🧠 **Powered by Gemini 2.5 Flash:** Generates optimized shell commands using Google's fastest reasoning model via the official `google-genai` SDK.
- 💻 **OS & Shell Aware:** Silently captures `platform.system()` (e.g., Darwin / macOS) and `$SHELL` (e.g., `zsh`, `bash`) so generated syntax matches your environment.
- 🎯 **Strict Structured JSON:** Enforces structured JSON output matching `{"commands": [{"command": "...", "description": "...", "risk_level": "...", "is_destructive": bool}]}`.
- 🚨 **Destructive Action Warnings:** Automatically prefixes dangerous or irreversible commands (file deletion, process termination, disk formatting) with **`🚨 [DESTRUCTIVE]`**.
- ⌨️ **Interactive TUI:** Arrow-key navigation using `questionary.select`.
- ✏️ **Editable Execution:** Once selected, commands drop into an editable input buffer (`questionary.text`) so you can review or tweak parameters before pressing Enter to run.
- 🛡️ **Robust Error Handling:** 
  - Markdown code-fence regex fallback in case the model wraps JSON in backticks.
  - Graceful handling of empty command arrays, API rate limits, timeouts, and network disconnects without stack traces.

---

## Installation & Setup

### 1. Run Automated Setup
AskRo includes an automated setup script that creates a virtual environment, installs dependencies, and configures permissions:

```bash
cd /Users/rohan/Documents/Workspace/AskRo
./setup.sh
```

### 2. Manual Setup (Alternative)
If you prefer setting it up manually:

```bash
# Create virtual environment
python3 -m venv .venv

# Activate and install dependencies
source .venv/bin/activate
pip install -r requirements.txt

# Make script executable
chmod +x askro.py
```

---

## Authentication

AskRo uses the official **Google GenAI SDK** (`google-genai`).

1. Obtain a free Gemini API key with your Google/Gmail account at [Google AI Studio](https://aistudio.google.com/app/apikey).
2. Export your key in your shell:
   ```bash
   export GEMINI_API_KEY="your-gemini-api-key"
   ```
3. *(Optional)* Alternatively, create a `~/.askro.env` file with:
   ```bash
   GEMINI_API_KEY=your-gemini-api-key
   ```
   AskRo will automatically load this file on startup.

---

## Shell Aliasing

To run `askro` from any directory in your terminal:

### For Zsh (`~/.zshrc`) — *macOS Default*
Add the alias to your `~/.zshrc`:
```bash
echo 'alias askro="/Users/rohan/Documents/Workspace/AskRo/.venv/bin/python /Users/rohan/Documents/Workspace/AskRo/askro.py"' >> ~/.zshrc
source ~/.zshrc
```

### For Bash (`~/.bashrc` or `~/.bash_profile`)
Add the alias to your `~/.bashrc`:
```bash
echo 'alias askro="/Users/rohan/Documents/Workspace/AskRo/.venv/bin/python /Users/rohan/Documents/Workspace/AskRo/askro.py"' >> ~/.bashrc
source ~/.bashrc
```

---

## Usage

### 1. Direct Natural Language Query
Pass your query directly as command-line arguments:
```bash
askro find files larger than 100MB in downloads
askro kill process running on port 3000
askro show top 5 memory consuming processes
askro create a tar.gz archive of the src folder
```

### 2. Interactive Mode
Run `askro` without arguments to launch the interactive prompt:
```bash
askro
```
```text
? What command do you need? (Type in plain English): compress videos in current folder
```

### 3. Selection & Execution Flow
1. **Selection:**
   ```text
   ? Select a command: (Use arrow keys)
    » [LOW] find ~/Downloads -type f -size +100M -exec ls -lh {} +  — List files larger than 100MB with human-readable sizes
      [LOW] du -ah ~/Downloads | grep -E "^[0-9.]+[MG]" | sort -hr | head -n 10  — Show largest files in Downloads directory
      🚫 Cancel / Exit
   ```
2. **Review Destructive Indicator:**
   ```text
   ? Select a command:
    » 🚨 [DESTRUCTIVE] [HIGH] kill -9 $(lsof -t -i:3000)  — Force kill process using TCP port 3000
      🚫 Cancel / Exit
   ```
3. **Edit Command:**
   ```text
   ? Edit command before executing: kill -9 $(lsof -t -i:3000)
   ```
4. **Native Execution:**
   Press `Enter` to run the command in your shell via `subprocess.run(shell=True)`.
