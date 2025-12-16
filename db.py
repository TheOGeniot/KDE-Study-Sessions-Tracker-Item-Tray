#!/usr/bin/env python3
import csv
from pathlib import Path
from typing import Optional

from models import StudySession


class SessionDatabase:
    """CSV-based session storage. All data persisted to sessions.csv and pauses.csv."""

    def __init__(self, csv_path: Optional[Path] = None):
        if csv_path is None:
            csv_path = Path.home() / '.local/share/study-session' / 'sessions.csv'
        self.csv_path = csv_path
        self.csv_path.parent.mkdir(parents=True, exist_ok=True)
        self.pauses_csv = self.csv_path.parent / 'pauses.csv'
        self.ensure_csv_headers()

    def ensure_csv_headers(self):
        """Ensure CSV files have headers if they don't exist."""
        if not self.csv_path.exists() or self.csv_path.stat().st_size == 0:
            with self.csv_path.open(mode='w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=[
                    'session_id', 'started_at', 'ended_at', 'total_duration_seconds',
                    'active_time_seconds', 'pause_count', 'total_pause_duration_seconds', 'notes'
                ])
                writer.writeheader()

        if not self.pauses_csv.exists() or self.pauses_csv.stat().st_size == 0:
            with self.pauses_csv.open(mode='w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=[
                    'id', 'session_id', 'reason', 'started_at', 'ended_at', 'duration_seconds'
                ])
                writer.writeheader()

    def save_session(self, session: StudySession, notes: str = ""):
        """Save a session to CSV (sessions.csv) and log its pauses (pauses.csv)."""
        summary = session.end()
        if not summary:
            if session.start_time and session.end_time and not session.is_running:
                total_duration = int((session.end_time - session.start_time).total_seconds())
                total_pause = session.pause_manager.get_session_total_pause_time(session.id)
                pause_count = session.pause_manager.get_session_pause_count(session.id)
                summary = {
                    'session_id': session.id,
                    'total_duration': total_duration,
                    'total_pause': total_pause,
                    'active_time': total_duration - total_pause,
                    'pause_count': pause_count,
                    'pauses': session.pause_manager.get_session_pauses(session.id)
                }
            else:
                return

        # Append session to sessions.csv
        session_row = {
            'session_id': summary.get('session_id'),
            'started_at': session.start_time.isoformat() if session.start_time else '',
            'ended_at': session.end_time.isoformat() if session.end_time else '',
            'total_duration_seconds': summary.get('total_duration', 0),
            'active_time_seconds': summary.get('active_time', 0),
            'pause_count': summary.get('pause_count', 0),
            'total_pause_duration_seconds': summary.get('total_pause', 0),
            'notes': notes or ''
        }
        with self.csv_path.open(mode='a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'session_id', 'started_at', 'ended_at', 'total_duration_seconds',
                'active_time_seconds', 'pause_count', 'total_pause_duration_seconds', 'notes'
            ])
            writer.writerow(session_row)

        # Append pauses to pauses.csv
        for pause in summary.get('pauses', []):
            pause_row = {
                'id': pause.id,
                'session_id': pause.session_id,
                'reason': pause.reason or '',
                'started_at': pause.started_at.isoformat() if pause.started_at else '',
                'ended_at': pause.ended_at.isoformat() if pause.ended_at else '',
                'duration_seconds': pause.duration_seconds or 0
            }
            with self.pauses_csv.open(mode='a', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=[
                    'id', 'session_id', 'reason', 'started_at', 'ended_at', 'duration_seconds'
                ])
                writer.writerow(pause_row)

    def log_event(self, session_id, event_type, event_data):
        """Log an event (e.g., pause, mood, thoughts). Events stored inline in session notes."""
        pass  # Events logged via save_session; can extend with events.csv if needed

    def fetch_unsynced_sessions(self):
        """Read all sessions from CSV. Since CSV has no sync flag, return all."""
        sessions = []
        if not self.csv_path.exists():
            return sessions
        with self.csv_path.open(mode='r', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row:
                    sessions.append(dict(row))
        return sessions

    def fetch_unsynced_pauses_for_session(self, session_id: str):
        """Read all pauses for a given session from pauses.csv."""
        pauses = []
        if not self.pauses_csv.exists():
            return pauses
        with self.pauses_csv.open(mode='r', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row and row.get('session_id') == session_id:
                    pauses.append(dict(row))
        return pauses

    def delete_pauses_by_ids(self, pause_ids):
        """Remove pause rows from pauses.csv by ID."""
        if not pause_ids or not self.pauses_csv.exists():
            return 0
        pause_ids_set = set(pause_ids)
        rows = []
        deleted = 0
        with self.pauses_csv.open(mode='r', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('id') not in pause_ids_set:
                    rows.append(row)
                else:
                    deleted += 1

        with self.pauses_csv.open(mode='w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'id', 'session_id', 'reason', 'started_at', 'ended_at', 'duration_seconds'
            ])
            writer.writeheader()
            writer.writerows(rows)
        return deleted

    def delete_session_by_session_id(self, session_id: str):
        """Remove a session row from sessions.csv by session_id."""
        if not self.csv_path.exists():
            return 0
        rows = []
        deleted = 0
        with self.csv_path.open(mode='r', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('session_id') != session_id:
                    rows.append(row)
                else:
                    deleted += 1

        with self.csv_path.open(mode='w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'session_id', 'started_at', 'ended_at', 'total_duration_seconds',
                'active_time_seconds', 'pause_count', 'total_pause_duration_seconds', 'notes'
            ])
            writer.writeheader()
            writer.writerows(rows)
        return deleted
