#!/usr/bin/env python3
import sqlite3
import json
import csv
from pathlib import Path
from datetime import datetime
from typing import Optional

from models import StudySession

class SessionDatabase:
    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            db_path = Path.home() / '.local/share/study-session' / 'sessions.db'
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_db()
    
    def init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT UNIQUE,
                started_at TIMESTAMP,
                ended_at TIMESTAMP,
                total_duration_seconds INTEGER,
                pause_count INTEGER DEFAULT 0,
                total_pause_duration_seconds INTEGER DEFAULT 0,
                notes TEXT,
                synced_to_n8n BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pauses (
                id TEXT PRIMARY KEY,
                session_id TEXT,
                reason TEXT,
                started_at TIMESTAMP,
                ended_at TIMESTAMP,
                duration_seconds INTEGER,
                synced_to_n8n BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(session_id) REFERENCES sessions(session_id)
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS session_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                event_type TEXT,
                event_data TEXT,
                timestamp TIMESTAMP,
                synced_to_n8n BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            )
        ''')
        # Ensure columns exist on older DBs (simple migrations)
        try:
            # sessions table
            cursor.execute('PRAGMA table_info(sessions)')
            session_cols = {row[1] for row in cursor.fetchall()}
            def add_col_if_missing(table, col_sql):
                cursor.execute(f'ALTER TABLE {table} ADD COLUMN {col_sql}')
            if 'pause_count' not in session_cols:
                add_col_if_missing('sessions', 'pause_count INTEGER DEFAULT 0')
            if 'total_pause_duration_seconds' not in session_cols:
                add_col_if_missing('sessions', 'total_pause_duration_seconds INTEGER DEFAULT 0')
            if 'notes' not in session_cols:
                add_col_if_missing('sessions', 'notes TEXT')
            if 'synced_to_n8n' not in session_cols:
                add_col_if_missing('sessions', 'synced_to_n8n BOOLEAN DEFAULT 0')
            if 'created_at' not in session_cols:
                add_col_if_missing('sessions', 'created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP')

            # pauses table
            cursor.execute('PRAGMA table_info(pauses)')
            pause_cols = {row[1] for row in cursor.fetchall()}
            if 'reason' not in pause_cols:
                add_col_if_missing('pauses', 'reason TEXT')
            if 'synced_to_n8n' not in pause_cols:
                add_col_if_missing('pauses', 'synced_to_n8n BOOLEAN DEFAULT 0')
            if 'created_at' not in pause_cols:
                add_col_if_missing('pauses', 'created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
        except sqlite3.OperationalError:
            # Swallow errors if columns already added in concurrent runs
            pass
        conn.commit()
        conn.close()
    
    def save_session(self, session: StudySession, notes: str = ""):
        summary = session.end()
        if not summary:
            # If already ended, reconstruct a minimal summary for persistence
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
        conn = sqlite3.connect(self.db_path)
        conn.execute('''
            INSERT OR REPLACE INTO sessions 
            (session_id, started_at, ended_at, total_duration_seconds, pause_count, total_pause_duration_seconds, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            summary['session_id'],
            session.start_time.isoformat(),
            session.end_time.isoformat(),
            summary['total_duration'],
            summary['pause_count'],
            summary['total_pause'],
            notes
        ))
        for pause in summary['pauses']:
            conn.execute('''
                INSERT OR REPLACE INTO pauses 
                (id, session_id, reason, started_at, ended_at, duration_seconds)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                pause.id, pause.session_id, pause.reason,
                pause.started_at.isoformat() if pause.started_at else None,
                pause.ended_at.isoformat() if pause.ended_at else None,
                pause.duration_seconds
            ))
        conn.commit()
        conn.close()

    def append_session_csv(self, summary: dict, notes: str = ""):
        """Append a session row to CSV at the same location as the DB."""
        out_path = self.db_path.parent / 'sessions.csv'
        out_path.parent.mkdir(parents=True, exist_ok=True)
        headers = [
            'session_id', 'started_at', 'ended_at', 'total_duration_seconds',
            'active_time_seconds', 'pause_count', 'total_pause_duration_seconds', 'notes'
        ]
        row = {
            'session_id': summary.get('session_id'),
            'started_at': summary.get('started_at') or '',
            'ended_at': summary.get('ended_at') or '',
            'total_duration_seconds': summary.get('total_duration', 0),
            'active_time_seconds': summary.get('active_time', 0),
            'pause_count': summary.get('pause_count', 0),
            'total_pause_duration_seconds': summary.get('total_pause', 0),
            'notes': notes or ''
        }
        # If started/ended not provided in summary, derive from session-events is non-trivial.
        # Expect caller to pass them when available.
        write_header = not out_path.exists() or out_path.stat().st_size == 0
        with out_path.open(mode='a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            if write_header:
                writer.writeheader()
            writer.writerow(row)
    
    def log_event(self, session_id, event_type, event_data):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO session_events (session_id, event_type, event_data, timestamp)
            VALUES (?, ?, ?, ?)
        ''', (session_id, event_type, json.dumps(event_data), datetime.now()))
        conn.commit()
        conn.close()

    # --- Sync helpers for n8n local-storage workflow ---
    def fetch_unsynced_sessions(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('''
            SELECT session_id, started_at, ended_at, total_duration_seconds, pause_count,
                   total_pause_duration_seconds, notes
            FROM sessions
            WHERE IFNULL(synced_to_n8n, 0) = 0 AND ended_at IS NOT NULL
        ''')
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return rows

    def fetch_unsynced_pauses_for_session(self, session_id: str):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, session_id, reason, started_at, ended_at, duration_seconds
            FROM pauses
            WHERE session_id = ? AND IFNULL(synced_to_n8n, 0) = 0
        ''', (session_id,))
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return rows

    def delete_pauses_by_ids(self, pause_ids):
        if not pause_ids:
            return 0
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.executemany('DELETE FROM pauses WHERE id = ?', [(pid,) for pid in pause_ids])
        deleted = cursor.rowcount
        conn.commit()
        conn.close()
        return deleted

    def delete_session_by_session_id(self, session_id: str):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        # Ensure child pauses are removed if any remain
        cursor.execute('DELETE FROM pauses WHERE session_id = ?', (session_id,))
        cursor.execute('DELETE FROM sessions WHERE session_id = ?', (session_id,))
        deleted = cursor.rowcount
        conn.commit()
        conn.close()
        return deleted
