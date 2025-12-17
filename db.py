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
        # Catalogs and profiles
        self.location_catalog_csv = self.csv_path.parent / 'location_catalog.csv'
        self.equipment_catalog_csv = self.csv_path.parent / 'equipment_catalog.csv'
        self.profiles_csv = self.csv_path.parent / 'profiles.csv'
        self.settings_csv = self.csv_path.parent / 'settings.csv'
        self.ensure_csv_headers()

    def ensure_csv_headers(self):
        """Ensure CSV files have headers; migrate old headers to include new columns."""
        session_fields = [
            'session_id', 'started_at', 'ended_at', 'total_duration_seconds',
            'active_time_seconds', 'pause_count', 'total_pause_duration_seconds', 'notes',
            'location', 'equipment'
        ]
        # Create or migrate sessions.csv
        if not self.csv_path.exists() or self.csv_path.stat().st_size == 0:
            with self.csv_path.open(mode='w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=session_fields)
                writer.writeheader()
        else:
            # Migrate existing file if missing new columns
            with self.csv_path.open(mode='r', newline='') as f:
                reader = csv.DictReader(f)
                existing_fields = reader.fieldnames or []
                needs_migration = any(col not in existing_fields for col in ['location', 'equipment'])
                if needs_migration:
                    rows = list(reader)
            if 'needs_migration' in locals() and needs_migration:
                # Re-write with new headers; fill missing fields with ''
                with self.csv_path.open(mode='w', newline='') as fw:
                    writer = csv.DictWriter(fw, fieldnames=session_fields)
                    writer.writeheader()
                    for row in rows:
                        row = row or {}
                        for col in session_fields:
                            if col not in row:
                                row[col] = ''
                        writer.writerow(row)

        if not self.pauses_csv.exists() or self.pauses_csv.stat().st_size == 0:
            with self.pauses_csv.open(mode='w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=[
                    'id', 'session_id', 'reason', 'started_at', 'ended_at', 'duration_seconds'
                ])
                writer.writeheader()

        # Initialize catalogs and profiles if missing
        if not self.location_catalog_csv.exists() or self.location_catalog_csv.stat().st_size == 0:
            with self.location_catalog_csv.open(mode='w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=['location'])
                writer.writeheader()
                for loc in ['home', 'class', 'transports']:
                    writer.writerow({'location': loc})
        if not self.equipment_catalog_csv.exists() or self.equipment_catalog_csv.stat().st_size == 0:
            with self.equipment_catalog_csv.open(mode='w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=['equipment'])
                writer.writeheader()
        if not self.profiles_csv.exists() or self.profiles_csv.stat().st_size == 0:
            with self.profiles_csv.open(mode='w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=['name', 'location', 'equipment'])
                writer.writeheader()

    def save_session(self, session: StudySession, notes: str = "", location: str = "", equipment: str = ""):
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
            'notes': notes or '',
            'location': location or '',
            'equipment': equipment or ''
        }
        with self.csv_path.open(mode='a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'session_id', 'started_at', 'ended_at', 'total_duration_seconds',
                'active_time_seconds', 'pause_count', 'total_pause_duration_seconds', 'notes',
                'location', 'equipment'
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
                'active_time_seconds', 'pause_count', 'total_pause_duration_seconds', 'notes',
                'location', 'equipment'
            ])
            writer.writeheader()
            writer.writerows(rows)
        return deleted

    # Catalog and profile helpers
    def get_location_catalog(self):
        items = []
        if self.location_catalog_csv.exists():
            with self.location_catalog_csv.open(mode='r', newline='') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get('location'):
                        items.append(row['location'])
        return items

    def add_location(self, name: str):
        name = (name or '').strip()
        if not name:
            return False
        existing = set(self.get_location_catalog())
        if name in existing:
            return True
        with self.location_catalog_csv.open(mode='a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['location'])
            writer.writerow({'location': name})
        return True

    def remove_location(self, name: str):
        if not self.location_catalog_csv.exists():
            return 0
        rows = []
        removed = 0
        with self.location_catalog_csv.open(mode='r', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('location') != name:
                    rows.append(row)
                else:
                    removed += 1
        with self.location_catalog_csv.open(mode='w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['location'])
            writer.writeheader(); writer.writerows(rows)
        return removed

    def get_equipment_catalog(self):
        items = []
        if self.equipment_catalog_csv.exists():
            with self.equipment_catalog_csv.open(mode='r', newline='') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get('equipment'):
                        items.append(row['equipment'])
        return items

    def add_equipment(self, name: str):
        name = (name or '').strip()
        if not name:
            return False
        existing = set(self.get_equipment_catalog())
        if name in existing:
            return True
        with self.equipment_catalog_csv.open(mode='a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['equipment'])
            writer.writerow({'equipment': name})
        return True

    def remove_equipment(self, name: str):
        if not self.equipment_catalog_csv.exists():
            return 0
        rows = []
        removed = 0
        with self.equipment_catalog_csv.open(mode='r', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('equipment') != name:
                    rows.append(row)
                else:
                    removed += 1
        with self.equipment_catalog_csv.open(mode='w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['equipment'])
            writer.writeheader(); writer.writerows(rows)
        return removed

    def get_profiles(self):
        profiles = []
        if self.profiles_csv.exists():
            with self.profiles_csv.open(mode='r', newline='') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row:
                        profiles.append({'name': row.get('name', ''), 'location': row.get('location', ''), 'equipment': row.get('equipment', '')})
        return profiles

    def get_profile(self, name: str):
        name = (name or '').strip()
        if not name or not self.profiles_csv.exists():
            return None
        with self.profiles_csv.open(mode='r', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('name') == name:
                    return {'name': row.get('name', ''), 'location': row.get('location', ''), 'equipment': row.get('equipment', '')}
        return None

    def save_profile(self, name: str, location: str = "", equipment: str = ""):
        name = (name or '').strip()
        if not name:
            return False
        rows = []
        updated = False
        if self.profiles_csv.exists():
            with self.profiles_csv.open(mode='r', newline='') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get('name') == name:
                        rows.append({'name': name, 'location': location or '', 'equipment': equipment or ''})
                        updated = True
                    else:
                        rows.append(row)
        if not updated:
            rows.append({'name': name, 'location': location or '', 'equipment': equipment or ''})
        with self.profiles_csv.open(mode='w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['name', 'location', 'equipment'])
            writer.writeheader(); writer.writerows(rows)
        return True

    def delete_profile(self, name: str):
        if not self.profiles_csv.exists():
            return 0
        rows = []
        removed = 0
        with self.profiles_csv.open(mode='r', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('name') != name:
                    rows.append(row)
                else:
                    removed += 1
        with self.profiles_csv.open(mode='w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['name', 'location', 'equipment'])
            writer.writeheader(); writer.writerows(rows)
        return removed

    def rename_profile(self, old_name: str, new_name: str):
        if not self.profiles_csv.exists():
            return False
        new_name = (new_name or '').strip()
        if not new_name:
            return False
        rows = []
        changed = False
        with self.profiles_csv.open(mode='r', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('name') == old_name:
                    row['name'] = new_name
                    changed = True
                rows.append(row)
        if not changed:
            return False
        with self.profiles_csv.open(mode='w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['name', 'location', 'equipment'])
            writer.writeheader(); writer.writerows(rows)
        return True

    def get_setting(self, key: str, default: str = ""):
        """Get a setting value by key"""
        key = (key or '').strip()
        if not key or not self.settings_csv.exists():
            return default
        with self.settings_csv.open(mode='r', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('key') == key:
                    return row.get('value', default)
        return default

    def set_setting(self, key: str, value: str = ""):
        """Set a setting value by key"""
        key = (key or '').strip()
        if not key:
            return False
        rows = []
        updated = False
        if self.settings_csv.exists():
            with self.settings_csv.open(mode='r', newline='') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get('key') == key:
                        rows.append({'key': key, 'value': value or ''})
                        updated = True
                    else:
                        rows.append(row)
        if not updated:
            rows.append({'key': key, 'value': value or ''})
        with self.settings_csv.open(mode='w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['key', 'value'])
            writer.writeheader(); writer.writerows(rows)
        return True

    def get_setting(self, key: str, default: str = ""):
        """Get a setting value by key"""
        key = (key or '').strip()
        if not key or not self.settings_csv.exists():
            return default
        with self.settings_csv.open(mode='r', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('key') == key:
                    return row.get('value', default)
        return default

    def set_setting(self, key: str, value: str = ""):
        """Set a setting value by key"""
        key = (key or '').strip()
        if not key:
            return False
        rows = []
        updated = False
        if self.settings_csv.exists():
            with self.settings_csv.open(mode='r', newline='') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get('key') == key:
                        rows.append({'key': key, 'value': value or ''})
                        updated = True
                    else:
                        rows.append(row)
        if not updated:
            rows.append({'key': key, 'value': value or ''})
        with self.settings_csv.open(mode='w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['key', 'value'])
            writer.writeheader(); writer.writerows(rows)
        return True
