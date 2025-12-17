#!/usr/bin/env python3
import os
import json
import asyncio
from datetime import datetime
import aiohttp
from PyQt5.QtCore import QObject, pyqtSignal

from db import SessionDatabase


class SessionAPIManager(QObject):
    status_changed = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        # Base URL and endpoints (relative or absolute). We only compose; no calls yet.
        self.base_url = os.getenv('N8N_BASE_URL', '').rstrip('/')
        log_ep = os.getenv('N8N_SESSION_LOG_ENDPOINT', 'session-log')
        pauses_ep = os.getenv('N8N_SESSION_PAUSES_ENDPOINT', 'session-pauses')

        def build_url(ep: str):
            if not ep:
                return None
            ep = ep.strip()
            if ep.startswith('http://') or ep.startswith('https://'):
                return ep.rstrip('/')
            if not self.base_url:
                return None
            return f"{self.base_url}/{ep.lstrip('/')}".rstrip('/')

        self.session_log_endpoint = build_url(log_ep)
        self.session_pauses_endpoint = build_url(pauses_ep)
        # Print composed endpoints for visibility
        print("[API] N8N base:", self.base_url or "(unset)")
        print("[API] session-log endpoint:", self.session_log_endpoint)
        print("[API] session-pauses endpoint:", self.session_pauses_endpoint)

        self.db = SessionDatabase()

    async def make_request(self, subcommand, params=None, session_id=None):
        # Placeholder: local event log + status only. No network.
        print(f"[API] make_request -> subcommand={subcommand}, session_id={session_id}, params={params or {}}")
        if session_id:
            self.db.log_event(session_id, subcommand, params or {})
        self.status_changed.emit(f"✅ {subcommand.capitalize()} (local)")
        return True

    def run_async(self, coro):
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)

    @staticmethod
    def _format_ts_for_api(ts: str) -> str:
        try:
            dt = datetime.fromisoformat(ts)
            original = dt.isoformat()
            dt = dt.replace(second=0, microsecond=0)
            formatted = dt.isoformat()
            if formatted != original:
                print(f"[API] format_ts: {original} -> {formatted}")
            return formatted
        except Exception:
            return ts

    async def sync_unsynced(self):
        # Prepare and send payloads to configured endpoints; only manual trigger uses this.
        print("[API] Sync: reading DB for unsynced sessions...")
        sessions = self.db.fetch_unsynced_sessions()
        if not sessions:
            self.status_changed.emit("✅ Nothing to sync")
            return True

        prepared = []
        print(f"[API] Sync: found {len(sessions)} session(s)")
        for s in sessions:
            try:
                print("[API] Session row:", json.dumps(s, indent=2))
            except Exception:
                print("[API] Session row:", s)
            session_payload = {
                'session_id': s['session_id'],
                'started_at': self._format_ts_for_api(s['started_at']) if s.get('started_at') else None,
                'ended_at': self._format_ts_for_api(s['ended_at']) if s.get('ended_at') else None,
                'total_duration_seconds': s.get('total_duration_seconds') or 0,
                'pause_count': s.get('pause_count') or 0,
                'total_pause_duration_seconds': s.get('total_pause_duration_seconds') or 0,
                'notes': s.get('notes') or '',
                'location': s.get('location') or '',
                'equipment': s.get('equipment') or ''
            }
            pauses = self.db.fetch_unsynced_pauses_for_session(s['session_id'])
            pause_payloads = [
                {
                    'id': p['id'],
                    'session_id': p['session_id'],
                    'reason': p.get('reason') or '',
                    'started_at': self._format_ts_for_api(p['started_at']) if p.get('started_at') else None,
                    'ended_at': self._format_ts_for_api(p['ended_at']) if p.get('ended_at') else None,
                    'duration_seconds': p.get('duration_seconds') or 0,
                }
                for p in pauses
            ]
            print(f"[API] Build payload: session-log -> {self.session_log_endpoint}")
            try:
                print(json.dumps(session_payload, indent=2))
            except Exception:
                print(session_payload)
            print(f"[API] Build payload: session-pauses -> {len(pause_payloads)} pause(s) to {self.session_pauses_endpoint}")
            if pause_payloads:
                try:
                    print(json.dumps(pause_payloads, indent=2))
                except Exception:
                    print(pause_payloads)
            prepared.append({'session': session_payload, 'pauses': pause_payloads})
        # If endpoints are not configured, keep local only.
        if not (self.session_log_endpoint and self.session_pauses_endpoint):
            self.status_changed.emit("⚠️ Sync skipped (endpoints not configured)")
            return False

        # Perform network calls; delete only upon success (2XX)
        # Continue all attempts even on 4XX or errors
        all_ok = True
        for item in prepared:
            s = item['session']
            print(f"[API] Sending session-log for session_id={s['session_id']}")
            ok = await self._post_json(self.session_log_endpoint, s)
            if not ok:
                all_ok = False
                self.status_changed.emit(f"⚠️ session-log failed for {s['session_id']}")
                print(f"[API] session-log FAILED for {s['session_id']}")
                # Continue to attempt pause sends even if session-log failed
            else:
                print(f"[API] session-log OK for {s['session_id']}; will queue deletions after pauses")
            sent_pause_ids = []
            for p in item['pauses']:
                print(f"[API] Sending session-pauses for pause_id={p['id']} (session {p['session_id']})")
                pok = await self._post_json(self.session_pauses_endpoint, p)
                if pok:
                    sent_pause_ids.append(p['id'])
                    print(f"[API] session-pauses OK -> store pause id for delete: {p['id']}")
                else:
                    all_ok = False
                    self.status_changed.emit(f"⚠️ session-pauses failed for pause {p['id']}")
                    print(f"[API] session-pauses FAILED for pause {p['id']}")
                    # Continue to next pause even on failure
            if sent_pause_ids:
                print(f"[API] Deleting {len(sent_pause_ids)} synced pause(s): {sent_pause_ids}")
                self.db.delete_pauses_by_ids(sent_pause_ids)
            if len(sent_pause_ids) == len(item['pauses']):
                print(f"[API] All pauses synced; deleting session {s['session_id']}")
                self.db.delete_session_by_session_id(s['session_id'])
            else:
                print(f"[API] Not all pauses synced; keeping session {s['session_id']} locally")

        if all_ok:
            self.status_changed.emit("✅ Sync completed")
        else:
            self.status_changed.emit("⚠️ Sync partially completed")
        return all_ok

    async def _post_json(self, url: str, payload: dict):
        if not url:
            return False
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    ok = 200 <= resp.status < 300
                    print(f"[API] POST {url} -> status {resp.status}")
                    return ok
        except asyncio.TimeoutError:
            print(f"[API] POST {url} -> timeout")
            return False
        except Exception as e:
            print(f"[API] POST {url} -> error: {e}")
            return False
