#!/usr/bin/env python3
import os
from datetime import datetime
from PyQt5.QtWidgets import QSystemTrayIcon, QMenu, QAction, QMessageBox
from PyQt5.QtGui import QIcon, QCursor
from PyQt5.QtCore import QTimer

from models import StudySession
from api import SessionAPIManager
from dialogs import InputDialog, SelectDialog, EnvironmentDialog, SettingsDialog

class StudySessionTray(QSystemTrayIcon):
    def __init__(self, app, parent=None):
        super().__init__(parent)
        self.app = app
        self.session = StudySession()
        self.api = SessionAPIManager()
        self.api.status_changed.connect(self.on_status_changed)
        self.session.status_changed.connect(self.on_session_status_changed)
        # Environment context (set via future dialog; defaults empty)
        self.current_location = ""
        self.current_equipment = ""
        # Clock icon with robust fallbacks: theme -> local svg -> generic
        icon = QIcon.fromTheme("clock")
        if icon.isNull():
            local_icon = QIcon("clock.svg")
            icon = local_icon if not local_icon.isNull() else QIcon.fromTheme("preferences-system-time")
        self.setIcon(icon)
        self.setToolTip("Study Session Manager\nRight-click for menu")
        self.menu = None
        self.status_action = None
        self.start_action = None
        self.pause_action = None
        self.continue_action = None
        self.end_action = None
        self.setup_menu()
        self.activated.connect(self.on_tray_activated)
        self.update_timer = QTimer(); self.update_timer.timeout.connect(self.update_menu_status); self.update_timer.start(1000)
    
    def on_tray_activated(self, reason):
        cursor_pos = QCursor.pos()
        if reason == QSystemTrayIcon.Context:
            if self.menu:
                self.menu.popup(cursor_pos)
        elif reason == QSystemTrayIcon.Trigger:
            # Some DEs prefer exec_ to force synchronous display
            if self.menu:
                self.menu.exec_(cursor_pos)
    
    def setup_menu(self):
        self.menu = QMenu()
        self.status_action = QAction("📊 Idle"); self.status_action.setEnabled(False)
        status_font = self.status_action.font(); status_font.setBold(True); self.status_action.setFont(status_font)
        self.menu.addAction(self.status_action); self.menu.addSeparator()
        # Place Sync near the top for visibility
        self.sync_action = QAction("🔄 Sync Now"); self.sync_action.triggered.connect(self.sync_now); self.menu.addAction(self.sync_action)
        # Keep references to prevent GC removing actions
        self.env_action = QAction("🌐 Change Environment…"); self.env_action.triggered.connect(self.change_environment); self.menu.addAction(self.env_action)
        self.start_action = QAction("▶️  Start Session"); self.start_action.triggered.connect(self.start_session); self.menu.addAction(self.start_action)
        self.pause_action = QAction("⏸️  Pause Session"); self.pause_action.triggered.connect(self.pause_session); self.menu.addAction(self.pause_action)
        self.continue_action = QAction("▶️  Continue Session"); self.continue_action.triggered.connect(self.continue_session); self.menu.addAction(self.continue_action)
        self.end_action = QAction("⏹️  End Session"); self.end_action.triggered.connect(self.end_session); self.menu.addAction(self.end_action)
        self.menu.addSeparator()
        self.settings_action = QAction("⚙️  Settings…"); self.settings_action.triggered.connect(self.open_settings); self.menu.addAction(self.settings_action)
        self.quit_action = QAction("❌ Quit"); self.quit_action.triggered.connect(self.quit_app); self.menu.addAction(self.quit_action)
        # Attach as tray context menu for KDE
        self.setContextMenu(self.menu)
        try:
            labels = [a.text() for a in self.menu.actions()]
            print("[Tray] Built menu:", labels)
        except Exception:
            pass
        # Initialize action states and visibility
        self.update_menu_action_states()
        running = self.session.is_running
        if self.env_action:
            self.env_action.setVisible(running)
        if self.sync_action:
            self.sync_action.setVisible(not running)
        # Ensure context menu is non-empty and visible
        self.setToolTip("Study Session Manager")
    
    def start_session(self):
        if self.session.is_running:
            self.show_notification("⚠️  Session Active", "End current session first", 3000); return
        # Prompt for environment before starting
        env_dialog = EnvironmentDialog(None, db=self.api.db, title="Select Environment", label="Pick location and equipment for this session")
        if env_dialog.exec_() != env_dialog.Accepted:
            return
        loc, eq = env_dialog.get_result()
        self.current_location = loc
        self.current_equipment = eq
        self.session.start();
        # Log locally only; no API call during session
        self.api.db.log_event(self.session.id, 'start', {})
        self.show_notification("🎯 Session Started", "Focus time activated!", 2000)
    
    def pause_session(self):
        if not self.session.is_running:
            self.show_notification("❌ No Active Session", "Start a session first", 2000); return
        dialog = InputDialog(None, "Pause Session", "Why are you pausing?", multiline=False)
        if dialog.exec_() == dialog.Accepted:
            reason = dialog.get_text()
            pause = self.session.pause(reason)
            if pause:
                params = {'pause_id': pause.id, 'reason': reason}
                # Local-only log during session
                self.api.db.log_event(self.session.id, 'pause', params)
                self.show_notification("⏸️  Session Paused", reason or "Paused", 2000)
    
    def continue_session(self):
        if not self.session.is_running:
            self.show_notification("❌ No Active Session", "Start a session first", 2000); return
        duration = self.session.resume()
        if duration > 0:
            params = {'pause_duration': duration}
            # Local-only log during session
            self.api.db.log_event(self.session.id, 'continue', params)
            self.show_notification("▶️  Session Resumed", "Back to focus mode!", 2000)
    
    def end_session(self):
        if not self.session.is_running:
            self.show_notification("❌ No Active Session", "Start a session first", 2000); return
        dialog = InputDialog(None, "End Session", "Session summary (optional):")
        if dialog.exec_() == dialog.Accepted:
            notes = dialog.get_text()
            summary = self.session.end()
            if summary:
                # Enrich summary with timestamps for CSV
                summary['started_at'] = self.session.start_time.isoformat() if self.session.start_time else None
                summary['ended_at'] = self.session.end_time.isoformat() if self.session.end_time else None
                # Save to CSV (sessions.csv and pauses.csv)
                self.api.db.save_session(self.session, notes, location=self.current_location, equipment=self.current_equipment)
                params = { 'notes': notes, 'active_time': summary['active_time'], 'total_pause': summary['total_pause'], 'pause_count': summary['pause_count'] }
                # Log end locally only; syncing happens via manual "Sync Now"
                self.api.db.log_event(self.session.id, 'end', params)
                duration_str = f"{int(summary['active_time'] / 60)} min"
                self.show_notification("✅ Session Ended", f"Logged: {duration_str}", 3000)
                self.session = StudySession(); self.session.status_changed.connect(self.on_session_status_changed)
    
    def log_thoughts(self):
        if not self.session.is_running:
            self.show_notification("💭 No Active Session", "Start a session to log thoughts", 2000); return
        dialog = InputDialog(None, "Log Thoughts", "What's on your mind?")
        if dialog.exec_() == dialog.Accepted:
            thoughts = dialog.get_text()
            if thoughts:
                params = {'notes': thoughts}
                # Local-only event log
                self.api.db.log_event(self.session.id, 'thoughts', params)
                self.show_notification("💭 Thought Logged", "Captured!", 2000)
    
    def log_mood(self):
        if not self.session.is_running:
            self.show_notification("😊 No Active Session", "Start a session to log mood", 2000); return
        moods = ["😊 Focused", "😐 Neutral", "😤 Frustrated", "😴 Tired", "🎉 Energized"]
        dialog = SelectDialog(None, "Log Mood", "How are you feeling?", moods)
        if dialog.exec_() == dialog.Accepted:
            mood = dialog.get_value()
            params = {'mood': mood}
            # Local-only event log
            self.api.db.log_event(self.session.id, 'mood', params)
            self.show_notification("😊 Mood Logged", mood, 2000)
    
    def set_focus_area(self):
        if not self.session.is_running:
            self.show_notification("🎯 No Active Session", "Start a session to set focus", 2000); return
        dialog = InputDialog(None, "Set Focus Area", "What are you working on?", multiline=False)
        if dialog.exec_() == dialog.Accepted:
            focus = dialog.get_text()
            if focus:
                params = {'focus': focus}
                # Local-only event log
                self.api.db.log_event(self.session.id, 'focus', params)
                self.show_notification("🎯 Focus Set", focus, 2000)
    
    def show_stats(self):
        sessions = self.api.db.fetch_unsynced_sessions()
        ended = [s for s in sessions if s.get('ended_at')]
        sessions_count = len(ended)
        def to_int(v):
            try:
                return int(v)
            except Exception:
                return 0
        total_seconds = sum(to_int(s.get('total_duration_seconds')) for s in ended)
        total_pauses = sum(to_int(s.get('pause_count')) for s in ended)
        total_hours = total_seconds / 3600 if total_seconds else 0
        msg = f"📊 Total Sessions: {sessions_count}\n⏱️  Total Time: {total_hours:.1f} hours\n⏸️  Total Pauses: {int(total_pauses)}"
        QMessageBox.information(None, "Session Statistics", msg)
    
    def run_command(self, subcommand, params=None, session_id=None):
        self.api.run_async(self.api.make_request(subcommand, params, session_id))

    def sync_now(self):
        # Manually trigger sync to n8n endpoints as configured in .env
        print("[Tray] Sync Now clicked — starting manual sync...")
        self.api.run_async(self.api.sync_unsynced())
    
    def on_status_changed(self, message):
        if self.status_action:
            self.status_action.setText(message)
    
    def on_session_status_changed(self, message):
        if self.status_action:
            self.status_action.setText(message)
    
    def update_menu_status(self):
        if self.session.is_running and self.session.start_time:
            elapsed = datetime.now() - self.session.start_time
            minutes = int(elapsed.total_seconds() / 60)
            active_pauses = self.session.pause_manager.get_active_pauses()
            status = f"⏸️  Paused ({minutes}m)" if active_pauses else f"▶️  Running ({minutes}m)"
            if self.status_action:
                self.status_action.setText(status)
        else:
            if self.status_action:
                self.status_action.setText("📊 Idle")
        # Keep action enabled states in sync
        self.update_menu_action_states()

    def update_menu_action_states(self):
        running = self.session.is_running
        paused = False
        if running:
            paused = bool(self.session.pause_manager.get_active_pauses())
        if self.start_action:
            self.start_action.setEnabled(not running)
        if self.pause_action:
            self.pause_action.setEnabled(running and not paused)
        if self.continue_action:
            self.continue_action.setEnabled(running and paused)
        if self.end_action:
            self.end_action.setEnabled(running)
        # Toggle visibility of Sync vs Change Environment
        if hasattr(self, 'env_action') and self.env_action:
            self.env_action.setVisible(running)
        if hasattr(self, 'sync_action') and self.sync_action:
            self.sync_action.setVisible(not running)
    
    def show_notification(self, title, message, duration=2000):
        self.showMessage(title, message, QSystemTrayIcon.Information, duration)
    
    def quit_app(self):
        self.hide(); self.app.quit()

    def change_environment(self):
        env_dialog = EnvironmentDialog(None, db=self.api.db, title="Change Environment", label="Update location and equipment")
        if env_dialog.exec_() == env_dialog.Accepted:
            new_loc, new_eq = env_dialog.get_result()
            if self.session.is_running:
                reply = QMessageBox.question(None,
                                             "Split Session?",
                                             "Changing environment will end the current session and start a new one. Continue?",
                                             QMessageBox.Yes | QMessageBox.No,
                                             QMessageBox.No)
                if reply != QMessageBox.Yes:
                    return
                # Finish current session with an auto note and current environment
                old_id = self.session.id
                # Close any active pause before ending
                if self.session.pause_manager.get_active_pauses():
                    try:
                        self.session.resume()
                    except Exception:
                        pass
                auto_note = f"continuing session {old_id}; environment changed"
                # End and persist old session with old env
                try:
                    self.session.end()
                except Exception:
                    pass
                self.api.db.save_session(self.session, auto_note, location=self.current_location, equipment=self.current_equipment)
                # Start a fresh session with new environment
                self.current_location = new_loc
                self.current_equipment = new_eq
                self.session = StudySession(); self.session.status_changed.connect(self.on_session_status_changed)
                self.session.start()
                self.api.db.log_event(self.session.id, 'start', {})
                self.show_notification("🌐 Environment Changed", f"New session started @ {new_loc or '—'}", 3000)
            else:
                # No active session: just update environment context
                self.current_location = new_loc
                self.current_equipment = new_eq
                self.show_notification("🌐 Environment Updated", f"Location: {new_loc or '—'}", 2000)

    def open_settings(self):
        dlg = SettingsDialog(None, db=self.api.db, title="Settings")
        if dlg.exec_() == dlg.Accepted:
            self.show_notification("⚙️  Settings Saved", "Catalogs updated", 2000)
