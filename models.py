#!/usr/bin/env python3
from dataclasses import dataclass
from datetime import datetime
import uuid
from PyQt5.QtCore import QObject, pyqtSignal

@dataclass
class Pause:
    id: str = None
    session_id: str = None
    reason: str = ""
    started_at: datetime = None
    ended_at: datetime = None
    duration_seconds: int = 0
    
    def __post_init__(self):
        if self.id is None:
            self.id = str(uuid.uuid4())[:8]
    
    @classmethod
    def create(cls, session_id: str, reason: str = "") -> 'Pause':
        return cls(session_id=session_id, reason=reason, started_at=datetime.now())
    
    def end(self) -> int:
        self.ended_at = datetime.now()
        self.duration_seconds = int((self.ended_at - self.started_at).total_seconds())
        return self.duration_seconds
    
    def is_active(self) -> bool:
        return self.started_at is not None and self.ended_at is None


class PauseManager:
    def __init__(self):
        self.active_pauses = {}
        self.completed_pauses = []
    
    def start_pause(self, session_id: str, reason: str = "") -> Pause:
        if session_id in self.active_pauses:
            return None
        pause = Pause.create(session_id, reason)
        self.active_pauses[session_id] = pause
        return pause
    
    def end_pause(self, session_id: str) -> int:
        if session_id not in self.active_pauses:
            return 0
        pause = self.active_pauses.pop(session_id)
        duration = pause.end()
        self.completed_pauses.append(pause)
        return duration
    
    def resume_session(self, session_id: str) -> int:
        return self.end_pause(session_id)
    
    def get_session_total_pause_time(self, session_id: str) -> int:
        return sum(p.duration_seconds for p in self.completed_pauses if p.session_id == session_id)
    
    def get_active_pauses(self) -> list:
        return list(self.active_pauses.values())
    
    def get_session_pauses(self, session_id: str) -> list:
        active = self.active_pauses.get(session_id)
        completed = [p for p in self.completed_pauses if p.session_id == session_id]
        return ([active] if active else []) + completed
    
    def get_session_pause_count(self, session_id: str) -> int:
        return len(self.get_session_pauses(session_id))


class StudySession(QObject):
    status_changed = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.id = None
        self.is_running = False
        self.start_time = None
        self.end_time = None
        self.pause_manager = PauseManager()
    
    def start(self) -> bool:
        if self.is_running:
            return False
        self.id = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.is_running = True
        self.start_time = datetime.now()
        self.pause_manager = PauseManager()
        self.status_changed.emit("▶️ Running")
        return True
    
    def pause(self, reason: str = "") -> Pause:
        if not self.is_running:
            return None
        pause = self.pause_manager.start_pause(self.id, reason)
        if pause:
            self.status_changed.emit("⏸️ Paused")
        return pause
    
    def resume(self) -> int:
        if not self.is_running:
            return 0
        duration = self.pause_manager.resume_session(self.id)
        if duration > 0:
            self.status_changed.emit("▶️ Running")
        return duration
    
    def end(self) -> dict:
        if not self.is_running:
            return {}
        
        # If there's an active pause when ending, use the pause start time as end time
        # and forget the pause (don't count it)
        active_pause = self.pause_manager.active_pauses.get(self.id)
        if active_pause:
            self.end_time = active_pause.started_at
            # Remove the active pause without completing it
            del self.pause_manager.active_pauses[self.id]
        else:
            self.end_time = datetime.now()
        
        total_duration = int((self.end_time - self.start_time).total_seconds())
        total_pause = self.pause_manager.get_session_total_pause_time(self.id)
        active_time = total_duration - total_pause
        pause_count = self.pause_manager.get_session_pause_count(self.id)
        self.is_running = False
        return {
            'session_id': self.id,
            'total_duration': total_duration,
            'total_pause': total_pause,
            'active_time': active_time,
            'pause_count': pause_count,
            'pauses': self.pause_manager.get_session_pauses(self.id)
        }
