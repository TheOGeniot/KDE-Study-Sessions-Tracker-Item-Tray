# Study Session Manager (PyQt5 Tray)

A clean, modular KDE-friendly system tray app to manage study sessions with start, pause, continue, and end actions. Tracks pauses with reasons, logs events locally to SQLite, and optionally syncs to an N8N backend.

## Project Structure

- `study_session_tray_standalone.py`: Entrypoint. Loads env, initializes Qt, shows tray UI.
- `tray.py`: Tray UI and menu actions (Start, Pause, Continue, End, stats, notifications).
- `models.py`: Core domain (Pause, PauseManager, StudySession).
- `db.py`: Local persistence (SQLite schema, session/pauses/events logging).
- `api.py`: Optional N8N integration (async HTTP with local fallback).
- `dialogs.py`: Polished input/select dialogs used by tray actions.

## Setup

Requirements:
- Python 3.10+
- KDE/Plasma or a system tray-capable desktop (X11/Wayland)

Install dependencies:

```bash
pip3 install -r requirements.txt
```

Quick setup:

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

Use the standalone entrypoint:

```bash
python3 "./study_session_tray_standalone.py"
```

You should see a tray icon; right-click (and left-click) opens the menu.

## Features

- Start session: begins tracking focus time
- Pause session: capture a reason; multiple pauses per session supported
- Continue session: resume from pause
- End session: logs session summary (active time, pause count, total pause)
- Log thoughts, mood, and focus area during the session
- View summary stats from local SQLite database
- Desktop notifications for actions

## Storage

- SQLite DB: `~/.local/share/study-session/sessions.db`
- Tables: `sessions`, `pauses`, `session_events`
- Timestamps stored in ISO-8601 strings for Python 3.12 compatibility

## N8N Local-Storage Workflow Sync

- When a session ends, the app attempts to sync any unsynced sessions/pauses to N8N.
- Endpoints used:
  - `POST /session-log`: one call per session (final summary)
  - `POST /session-pauses`: one call per pause belonging to that session
- Timestamp format: ISO-8601 with seconds zeroed (e.g. `2025-12-16T11:26:00`).
- Deletion policy:
  - Successfully posted pauses are deleted from local DB.
  - The session row is deleted only if it and all its pauses were posted successfully.
- If `N8N_BASE_URL` is unset, sync is skipped and data remains local.

## Contributing / Extending

- Keep modules small and focused:
  - UI logic in `tray.py`
  - Domain in `models.py`
  - Persistence in `db.py`
  - Integrations in `api.py`
- Prefer non-blocking operations; use `SessionAPIManager.run_async(...)` for async requests.
- For icons, use theme-aware icons via `QIcon.fromTheme("accessories-text-editor")` or provide a local fallback.

## Troubleshooting

- Tray not visible: ensure your desktop environment shows system tray icons; check hidden icons.
- Icon missing: provide a valid fallback icon file or change the theme icon name.
- Menu not opening: KDE requires `setContextMenu(self.menu)`; this is set in `tray.py`.
- Python warnings:
  - Async loop: uses `asyncio.get_running_loop()` to avoid deprecation.
  - SQLite datetime: timestamps stored as strings to avoid adapter deprecation.
