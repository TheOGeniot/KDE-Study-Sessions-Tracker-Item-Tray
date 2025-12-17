# Study Session Manager (PyQt5 Tray)

> **Purpose**: Personal study data collection for AI-driven productivity optimization  
> **Status**: Prototype — Functional for data collection, not production-ready  
> **Development**: This project is entirely vibecoded  
> A KDE-friendly system tray app to track study sessions locally and export data to N8N for processing. Built to gather rich session metadata (pauses, reasons, timestamps, notes) as training data for a future personal AI that maximizes productivity and performance.

Collect study session data with pause tracking, mood logging, focus areas, and environment context (location + equipment). All data stored locally in CSV only, with manual sync to N8N webhooks for ingestion into your ML pipeline.

## Project Structure

- `study_session_tray_standalone.py`: Entrypoint. Loads env, initializes Qt, shows tray UI.
- `tray.py`: Tray UI and menu actions (Start, Pause, Continue, End, stats, notifications).
- `models.py`: Core domain (Pause, PauseManager, StudySession).
- `db.py`: Local persistence (CSV storage for sessions/pauses, catalogs, and profiles).
- `api.py`: Optional N8N integration (async HTTP with local fallback).
- `dialogs.py`: Polished input/select dialogs used by tray actions.

## Setup

Requirements:
- Python 3.10+
- KDE/Plasma or a system tray-capable desktop (X11/Wayland)

Install dependencies (no virtualenv by default):

```bash
pip3 install --user -r requirements.txt
```

Quick setup (defaults to no venv):

```bash
chmod +x ./setup.sh
./setup.sh --run
```

Optional: set N8N base URL via `.env` in the project root:

```env
N8N_BASE_URL=https://your-n8n-host.example.com
# Optional endpoint paths (relative or absolute). If relative, they are
# appended to N8N_BASE_URL. Absolute URLs take precedence as-is.
N8N_SESSION_LOG_ENDPOINT=session-log
N8N_SESSION_PAUSES_ENDPOINT=session-pauses
```

## Run

Run the tray app:

```bash
python3 "./study_session_tray_standalone.py"
```

You should see a tray icon; right-click (and left-click) opens the menu.

## Features

**Data Collection:**
- Start session: begins tracking focus time
- Pause session: capture pause reason (e.g., "distraction", "bio break")
- Continue session: resume from pause
- End session: log session summary (active time, pause count, total pause duration, optional notes)
- Log thoughts, mood (5-point scale), and focus area during the session
- View summary stats computed from local CSV data

**Storage & Export:**
- All data stays local by default (CSV only)
- Manual sync to N8N via "🔄 Sync Now" button for centralized processing
- Rich metadata: timestamps, durations, pause reasons, mood, focus area, notes, location, equipment

## Storage

All data stored in CSV format in `~/.local/share/study-session/`:

- **sessions.csv**: One row per ended session
  - Columns: `session_id`, `started_at`, `ended_at`, `total_duration_seconds`, `active_time_seconds`, `pause_count`, `total_pause_duration_seconds`, `notes`, `location`, `equipment`
- **pauses.csv**: One row per pause within a session
  - Columns: `id`, `session_id`, `reason`, `started_at`, `ended_at`, `duration_seconds`
- **location_catalog.csv**: Preset and user-added locations (defaults: home, class, transports)
- **equipment_catalog.csv**: User-added equipment inventory (starts empty)
- **profiles.csv**: Saved environment profiles (`name, location, equipment`)

Simple, portable, and directly feedable into your ML pipeline.

## N8N Manual Sync (via "Sync Now" button)

**Sync is triggered manually by clicking "🔄 Sync Now" in the tray menu, not automatically.**

Use this to push collected session data to N8N for processing, storage, or ML training pipelines.

- For each unsynced session in local CSVs:
  - `POST /session-log`: one call per session (final summary with timestamps, durations, notes)
  - For each pause in that session:
    - `POST /session-pauses`: one call per pause (reason, started_at, ended_at, duration)
  - Environment context included in session-log: `location`, `equipment`
- Timestamp format: ISO-8601 with seconds zeroed (e.g. `2025-12-16T11:26:00`) for cleaner data
- **Robust error handling**: All endpoints are attempted; failures do not stop the sync
- **Deletion policy**:
  - Pauses: deleted from DB only if they posted successfully (2XX status)
  - Sessions: deleted from DB only if the session posted AND all its pauses posted
  - Failed/4XX entries remain in the DB for retry on next "Sync Now"
- Console logging: Full trace of DB reads, payload construction, sending, and deletions for debugging
- If `N8N_BASE_URL` is unset, sync button is available but will warn that endpoints are not configured

## Known Limitations & TODO

**Current Limitations (acceptable for data collection phase):**
- No authentication: N8N webhooks are called without auth headers or tokens
- No request signing: Payloads are not signed or verified
- No user management: All sessions logged as `tray_standalone` user (local collection only)
- No rate limiting: Sync can hammer the N8N endpoint if many sessions exist
- No retry/backoff: Failed requests remain locally but are not automatically retried
- No offline queue: If N8N is down, data stays local; manual sync will retry all next time
- Desktop integration: Only tested on KDE/Plasma; may need adjustments for GNOME, etc.
- No keyboard shortcuts: No global hotkeys for session control

**Future Enhancements (as AI training progresses):**
- Add Bearer token or API key authentication to `.env` and `_post_json()`
- Request signing for data integrity verification
- Automatic daily/weekly sync scheduling
- Web dashboard to visualize collected data and trends
- Integration with calendar/focus time blocking
- Global hotkeys for quick session control
- Support for multiple study contexts or projects
- Mood-to-performance correlation analysis
- Export to CSV/JSON for external analysis

## Contributing / Extending

- Keep modules small and focused:
  - UI logic in `tray.py`
  - Domain in `models.py`
  - Persistence in `db.py`
  - Integrations in `api.py`
- Prefer non-blocking operations; use `SessionAPIManager.run_async(...)` for async requests.
- For icons, use theme-aware icons via `QIcon.fromTheme("clock")` with fallbacks.
- **To add authentication**: Update `_post_json()` in `api.py` to include auth headers or Bearer tokens from `.env`
- Consider adding `requests` library for simpler HTTP handling if complexity grows.

## Troubleshooting

- Tray not visible: ensure your desktop environment shows system tray icons; check hidden icons.
- Icon missing: provide a valid fallback icon file or change the theme icon name.
- Menu not opening: KDE requires `setContextMenu(self.menu)`; this is set in `tray.py`.
- Python warnings:
  - Async loop: uses `asyncio.get_running_loop()` to avoid deprecation.
  - CSV I/O: files are rewritten on deletions; ensure disk has space.
