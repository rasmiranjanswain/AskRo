#!/usr/bin/env bash
# Setup script for AskRo CLI Utility

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"

echo "=============================================="
echo "          Setting up AskRo CLI               "
echo "=============================================="

# 1. Check Python 3
if ! command -v python3 &>/dev/null; then
    echo "❌ Python 3 is required but not found in PATH."
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "✔ Found Python $PYTHON_VERSION"

# 2. Create virtual environment if not already present
if [ ! -d "$VENV_DIR" ]; then
    echo "📦 Creating virtual environment in $VENV_DIR..."
    python3 -m venv "$VENV_DIR"
else
    echo "✔ Virtual environment already exists at $VENV_DIR"
fi

# 3. Upgrade pip and install requirements
echo "📦 Installing required dependencies (google-genai, questionary)..."
"$VENV_DIR/bin/python" -m pip install --quiet --upgrade pip
"$VENV_DIR/bin/pip" install --quiet -r "$SCRIPT_DIR/requirements.txt"

# 4. Make askro.py executable
chmod +x "$SCRIPT_DIR/askro.py"

echo "✔ Dependencies installed successfully."
echo ""
echo "=============================================="
echo "          Shell Alias Configuration           "
echo "=============================================="
echo "Add the following alias to your shell configuration:"
echo ""
echo "For Zsh (~/.zshrc) [macOS Default]:"
echo "  echo 'alias askro=\"$VENV_DIR/bin/python $SCRIPT_DIR/askro.py\"' >> ~/.zshrc"
echo "  source ~/.zshrc"
echo ""
echo "For Bash (~/.bashrc):"
echo "  echo 'alias askro=\"$VENV_DIR/bin/python $SCRIPT_DIR/askro.py\"' >> ~/.bashrc"
echo "  source ~/.bashrc"
echo ""
echo "=============================================="
echo "             API Key Authentication           "
echo "=============================================="
echo "On first run, AskRo will ask you to choose a provider"
echo "and enter its API key (saved to ~/.askro/config.json)."
echo "Run 'askro --reconfigure' later to change it."
echo ""
echo "Get a free API key at: https://aistudio.google.com/app/apikey"
echo "=============================================="
echo "🎉 Setup complete! You can now run:"
echo "  $VENV_DIR/bin/python $SCRIPT_DIR/askro.py --help"
echo "=============================================="
