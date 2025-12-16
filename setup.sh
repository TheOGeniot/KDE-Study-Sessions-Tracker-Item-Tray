#!/usr/bin/env bash
set -euo pipefail

# Study Session Manager — Setup & Run Script
# Creates an optional virtualenv, installs dependencies, and optionally runs the app.

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${PROJECT_DIR}/.venv"
NO_VENV=0
RUN_APP=0

# ============================================================================
# Functions
# ============================================================================

usage() {
  cat <<EOF
Usage: ./setup.sh [OPTIONS]

Options:
  --no-venv         Skip venv creation; use system Python (not recommended)
  --venv <path>     Create/use a specific venv path (default: .venv)
  --run             Run the app after setup
  -h, --help        Show this help message

Examples:
  ./setup.sh                           # Create venv in .venv, install deps
  ./setup.sh --no-venv                 # Install deps to system Python
  ./setup.sh --run                     # Setup and run the app
  ./setup.sh --venv ~/my-venv --run    # Custom venv path and run

Environment:
  Configure N8N sync via .env:
    N8N_BASE_URL=https://your-n8n-host.example.com
    N8N_SESSION_LOG_ENDPOINT=session-log
    N8N_SESSION_PAUSES_ENDPOINT=session-pauses

Database & CSV:
  ~/.local/share/study-session/sessions.db  (SQLite)
  ~/.local/share/study-session/sessions.csv (CSV export)
EOF
}

log() {
  echo "[setup] $*"
}

error() {
  echo "[setup] ERROR: $*" >&2
  exit 1
}

# ============================================================================
# Parse Arguments
# ============================================================================

while [[ $# -gt 0 ]]; do
  case "$1" in
    --no-venv)
      NO_VENV=1
      shift
      ;;
    --run)
      RUN_APP=1
      shift
      ;;
    --venv)
      VENV_DIR="$2"
      shift 2
      ;;
    -h | --help)
      usage
      exit 0
      ;;
    *)
      error "Unknown option: $1"
      ;;
  esac
done

# ============================================================================
# Checks
# ============================================================================

# Verify Python 3 available
if ! command -v python3 >/dev/null 2>&1; then
  error "python3 not found. Please install Python 3.10 or later."
fi

PYTHON_BIN="python3"
PIP_BIN="pip3"

# ============================================================================
# Setup Virtual Environment (if requested)
# ============================================================================

if [[ "$NO_VENV" -eq 0 ]]; then
  log "Setting up virtual environment at: $VENV_DIR"
  if [[ ! -d "$VENV_DIR" ]]; then
    "$PYTHON_BIN" -m venv "$VENV_DIR"
    log "Created venv."
  else
    log "Venv already exists."
  fi

  # Activate venv and update tools
  # shellcheck disable=SC1091
  source "$VENV_DIR/bin/activate"
  PYTHON_BIN="${VENV_DIR}/bin/python"
  PIP_BIN="${VENV_DIR}/bin/pip"
  log "Activated venv."
else
  log "Skipping venv (using system Python)."
fi

# ============================================================================
# Install Dependencies
# ============================================================================

log "Upgrading pip..."
"$PIP_BIN" install --upgrade pip setuptools wheel >/dev/null 2>&1

if [[ -f "$PROJECT_DIR/requirements.txt" ]]; then
  log "Installing from requirements.txt..."
  "$PIP_BIN" install -r "$PROJECT_DIR/requirements.txt"
  log "Dependencies installed."
else
  log "requirements.txt not found; installing minimal deps..."
  "$PIP_BIN" install PyQt5 python-dotenv aiohttp
fi

# ============================================================================
# Configuration Check
# ============================================================================

if [[ ! -f "$PROJECT_DIR/.env" ]]; then
  log "No .env file found. Create one to configure N8N sync (optional):"
  log "  N8N_BASE_URL=https://your-n8n-instance.com/webhook"
  log "  N8N_SESSION_LOG_ENDPOINT=session-log"
  log "  N8N_SESSION_PAUSES_ENDPOINT=session-pauses"
fi

# ============================================================================
# Run Application (if requested)
# ============================================================================

if [[ "$RUN_APP" -eq 1 ]]; then
  log "Starting Study Session Manager..."
  "$PYTHON_BIN" "$PROJECT_DIR/study_session_tray_standalone.py"
else
  log "Setup complete!"
  log ""
  log "To run the app, use:"
  log "  $PYTHON_BIN \"$PROJECT_DIR/study_session_tray_standalone.py\""
fi
