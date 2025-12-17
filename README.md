# Study Session Manager (PyQt5 Tray)

> **Purpose**: Personal study data collection for AI-driven productivity optimization  
> **Status**: Functional prototype for local data collection  
> **Platform**: KDE/Plasma system tray app (Linux)

A lightweight, KDE-friendly system tray application for tracking study sessions with comprehensive session metadata. Collect session data locally (pauses, reasons, timestamps, notes, environment context), then manually sync to N8N webhooks for processing into your ML pipeline.

## Project Structure

- `study_session_tray_standalone.py`: Entrypoint. Loads env, initializes Qt, shows tray UI.
- `tray.py`: Tray UI and menu actions (Start, Pause, Continue, End, stats, notifications).
- `models.py`: Core domain (Pause, PauseManager, StudySession).
- `db.py`: Local persistence (CSV storage for sessions/pauses, catalogs, and profiles).
- `api.py`: Optional N8N integration (async HTTP with local fallback).
- `dialogs.py`: Polished input/select dialogs used by tray actions.

## Quick Start

1. **Install dependencies:**
   ```bash
   pip3 install --user -r requirements.txt
   ```

2. **Run the app:**
   ```bash
   python3 ./study_session_tray_standalone.py
   ```

3. **Access your data:**
   ```bash
   cd ~/.local/share/study-session/
   cat sessions.csv | column -t -s,
   ```

The app minimizes to system tray. Right-click the icon to start tracking. Your data is automatically saved to `~/.local/share/study-session/`.

## Setup

**Requirements:**
- Python 3.10+
- KDE/Plasma desktop or system tray-capable environment (X11/Wayland)

**Automated setup with script:**

```bash
chmod +x ./setup.sh
./setup.sh --run
```

## License

This project is licensed under the GNU General Public License v3.0 (GPL-3.0). See the `LICENSE` file in the repository root for the full license text and details on redistribution and modification.


**Optional: Configure N8N integration**

Create `.env` in the project root to enable webhook sync:

```env
N8N_BASE_URL=https://your-n8n-host.example.com
N8N_SESSION_LOG_ENDPOINT=session-log
N8N_SESSION_PAUSES_ENDPOINT=session-pauses
```

Endpoint paths can be relative (appended to base URL) or absolute URLs.

## Features

### Session Management
- **Start Session**: Begin tracking with one click
- **Pause/Continue**: Track focus interruptions with optional reason notes
- **End Session**: Conclude with optional session summary
- **Profile-Based Context**: Save location and equipment combinations for automatic session enrichment

### Environment Profiles
- **Create profiles** with location and equipment combinations
- **Select profiles** before or during sessions
- **Manage catalogs** of locations and equipment
- **Session context** is automatically captured with each session record

### Data Collection
- **Active time tracking**: Total session duration minus pause time
- **Pause metadata**: Reason, timestamp, duration for each pause
- **Session notes**: Optional summary captured at session end
- **Environment context**: Location and equipment automatically included in exported data

### Manual Sync to N8N
- **Click "Sync Now"**: Manually trigger data export to N8N webhooks
- **Robust delivery**: All endpoints attempted; failures do not prevent other sends
- **Selective deletion**: Data deleted from local CSV only after successful upload
- **Offline resilient**: Failed syncs keep data locally for retry on next "Sync Now"

## 📊 Your Data

**Location:** `~/.local/share/study-session/`

### Quick Access

```bash
# Navigate to your data
cd ~/.local/share/study-session/

# View all your files
ls -lh

# See all sessions (formatted table)
cat sessions.csv | column -t -s,

# Count total sessions
wc -l sessions.csv

# View today's log
tail -f logs/session_manager_*.log

# Export for backup
cp -r ~/.local/share/study-session/ ~/study-data-backup
```

### Data Files

| File | Purpose |
|------|---------|
| `sessions.csv` | All completed sessions with metadata |
| `pauses.csv` | Detailed pause records per session |
| `location_catalog.csv` | Available study locations |
| `equipment_catalog.csv` | Available equipment types |
| `profiles.csv` | Saved environment profiles |
| `settings.csv` | App preferences (last profile used, etc.) |
| `logs/` | Daily operation logs for debugging |

### Session Record Structure

Each row in `sessions.csv` contains:
- `session_id`: Unique session identifier (timestamp)
- `started_at`, `ended_at`: ISO-8601 timestamps
- `total_duration_seconds`: Total time (including pauses)
- `active_time_seconds`: Time spent actually studying
- `pause_count`: Number of interruptions
- `total_pause_duration_seconds`: Total break time
- `notes`: Your session summary (if provided)
- `location`: Where you studied
- `equipment`: What you used

### Pause Record Structure

Each row in `pauses.csv` contains:
- `id`: Unique pause identifier
- `session_id`: Associated session
- `reason`: Why you paused (if provided)
- `started_at`, `ended_at`: When the pause occurred
- `duration_seconds`: How long the pause lasted

## N8N Integration

**Manual sync via "Sync Now" button** — triggered from the tray menu when session is not running.

### Payload Format

For each unsynced session:
- `POST` to `N8N_SESSION_LOG_ENDPOINT` with session summary
- `POST` to `N8N_SESSION_PAUSES_ENDPOINT` for each pause (one request per pause)

**Session payload example:**
```json
{
  "session_id": "20251217_143000",
  "started_at": "2025-12-17T14:30:00",
  "ended_at": "2025-12-17T15:15:00",
  "total_duration_seconds": 2700,
  "pause_count": 2,
  "total_pause_duration_seconds": 300,
  "notes": "Good focus session",
  "location": "home",
  "equipment": "laptop"
}
```

**Pause payload example:**
```json
{
  "id": "abc123de",
  "session_id": "20251217_143000",
  "reason": "coffee break",
  "started_at": "2025-12-17T14:50:00",
  "ended_at": "2025-12-17T14:55:00",
  "duration_seconds": 300
}
```

### Sync Behavior

- **All attempts made**: If session-log fails, pauses are still sent
- **Selective deletion**: Only successful (2XX) uploads are deleted from local CSV
- **Failed data preserved**: Failed syncs keep data locally for retry on next "Sync Now"
- **Logging**: Full trace in `~/.local/share/study-session/logs/`
- **No auth**: Webhooks currently called without authentication (see TODO)

## Known Limitations

- **No authentication**: N8N webhooks called without auth headers (see Contributing)
- **No rate limiting**: Sync can hammer endpoints if many sessions exist locally
- **No automatic retry**: Failed requests stay local; manual "Sync Now" retries all
- **No offline queue**: If N8N is down, data stays local until next manual sync
- **No keyboard shortcuts**: No global hotkeys for session control
- **Desktop-specific**: Tested on KDE/Plasma; may need adjustments for GNOME/other DEs
- **Single instance only**: Enforced via `/tmp/study_session_tray.lock`

## Contributing

### Code Structure
- `study_session_tray_standalone.py`: App entrypoint, env setup, single-instance lock
- `tray.py`: System tray UI, menu actions, session lifecycle
- `models.py`: `StudySession`, `PauseManager`, `Pause` domain classes
- `db.py`: CSV persistence, catalog/profile management, settings
- `api.py`: N8N webhook integration, async HTTP, sync orchestration
- `dialogs.py`: Input dialogs, profile selection, settings UI
- `logger.py`: Centralized logging to file and console
- `utils.py`: Helper functions (connectivity checks)

### Adding Features
- **Authentication**: Update `_post_json()` in `api.py` to include Bearer token from `.env`
- **Keyboard shortcuts**: Use `QShortcut` or `QApplication.instance().installEventFilter()`
- **Auto-sync scheduling**: Use `QTimer` in `tray.py` to periodically call `sync_unsynced()`
- **Icons**: Use `QIcon.fromTheme("name")` with fallbacks; avoid hardcoded colors
- **Logging**: Use `logger` from `setup_logger()` for consistency

### Testing
- Run without tray: `N8N_BASE_URL=` python3 study_session_tray_standalone.py
- Check data: `cat ~/.local/share/study-session/sessions.csv`
- Watch logs: `tail -f ~/.local/share/study-session/logs/session_manager_*.log`
