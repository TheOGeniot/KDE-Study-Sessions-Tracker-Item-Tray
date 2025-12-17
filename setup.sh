#!/usr/bin/env bash
set -euo pipefail

# Study Session Manager — Setup & Run Script
# Creates an optional virtualenv, installs dependencies, and optionally runs the app.

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${PROJECT_DIR}/.venv"
# Default to NO VENV per project preference
NO_VENV=1
RUN_APP=0

# ============================================================================
# Functions
# ============================================================================

usage() {
  cat <<EOF
Usage: ./setup.sh [OPTIONS]

Options:
  --no-venv         Skip venv creation; use system Python (default)
  --venv <path>     Create/use a specific venv path (optional)
  --run             Run the app after setup
  -h, --help        Show this help message

Examples:
  ./setup.sh                           # Install deps with system Python (no venv)
  ./setup.sh --venv .venv              # Use a virtualenv at .venv
  ./setup.sh --run                     # Setup and run the app
  ./setup.sh --venv ~/my-venv --run    # Custom venv path and run

Environment:
  Configure N8N sync via .env:
    N8N_BASE_URL=https://your-n8n-host.example.com
    N8N_SESSION_LOG_ENDPOINT=session-log
    N8N_SESSION_PAUSES_ENDPOINT=session-pauses

Local Data (CSV):
  ~/.local/share/study-session/sessions.csv
  ~/.local/share/study-session/pauses.csv
  ~/.local/share/study-session/location_catalog.csv
  ~/.local/share/study-session/equipment_catalog.csv
  ~/.local/share/study-session/profiles.csv
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
if [[ "$NO_VENV" -eq 1 ]]; then
  "$PIP_BIN" install --user --upgrade pip setuptools wheel >/dev/null 2>&1 || true
else
  "$PIP_BIN" install --upgrade pip setuptools wheel >/dev/null 2>&1
fi

if [[ -f "$PROJECT_DIR/requirements.txt" ]]; then
  log "Installing from requirements.txt..."
  if [[ "$NO_VENV" -eq 1 ]]; then
    "$PIP_BIN" install --user -r "$PROJECT_DIR/requirements.txt"
  else
    "$PIP_BIN" install -r "$PROJECT_DIR/requirements.txt"
  fi
  log "Dependencies installed."
else
  log "requirements.txt not found; installing minimal deps..."
  if [[ "$NO_VENV" -eq 1 ]]; then
    "$PIP_BIN" install --user PyQt5 python-dotenv aiohttp
  else
    "$PIP_BIN" install PyQt5 python-dotenv aiohttp
  fi
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
  if [[ "$NO_VENV" -eq 1 ]]; then
    log "If python cannot import packages, ensure --user bin path is on PATH."
  fi
fi
