#!/usr/bin/env python3
from datetime import datetime
from PyQt5.QtWidgets import QSystemTrayIcon, QMenu, QAction, QMessageBox
from PyQt5.QtGui import QIcon, QCursor
from PyQt5.QtCore import QTimer

from models import StudySession
from api import SessionAPIManager
from dialogs import InputDialog, SelectDialog, EnvironmentDialog, SettingsDialog
from logger import setup_logger

logger = setup_logger('tray')

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
        self.last_profile = ""  # Track last used profile
        # Load last profile from persistent storage
        self._load_last_profile()
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
        # Update profile display after menu is set up
        self.update_profile_display()
    
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
        self.menu.addAction(self.status_action)
        self.profile_action = QAction("Profile: None"); self.profile_action.triggered.connect(self.change_profile)
        self.menu.addAction(self.profile_action)
        self.menu.addSeparator()
        # Place Sync near the top for visibility
        self.sync_action = QAction("🔄 Sync Now"); self.sync_action.triggered.connect(self.sync_now); self.menu.addAction(self.sync_action)
        # Keep references to prevent GC removing actions
        self.change_profile_action = QAction("📋 Change Profile…"); self.change_profile_action.triggered.connect(self.change_profile_during_session); self.menu.addAction(self.change_profile_action)
        self.start_action = QAction("▶️  Start Session"); self.start_action.triggered.connect(self.start_session); self.menu.addAction(self.start_action)
        self.pause_action = QAction("⏸️  Pause Session"); self.pause_action.triggered.connect(self.pause_session); self.menu.addAction(self.pause_action)
        self.continue_action = QAction("▶️  Continue Session"); self.continue_action.triggered.connect(self.continue_session); self.menu.addAction(self.continue_action)
        self.end_action = QAction("⏹️  End Session"); self.end_action.triggered.connect(self.end_session); self.menu.addAction(self.end_action)
        self.menu.addSeparator()
        self.settings_action = QAction("⚙️  Settings…"); self.settings_action.triggered.connect(self.open_settings); self.menu.addAction(self.settings_action)
        self.quit_action = QAction("❌ Quit"); self.quit_action.triggered.connect(self.quit_app); self.menu.addAction(self.quit_action)
        # Attach as tray context menu for KDE
        self.setContextMenu(self.menu)
        # Initialize action states and visibility
        self.update_menu_action_states()
        running = self.session.is_running
        if self.change_profile_action:
            self.change_profile_action.setVisible(running)
        if self.sync_action:
            self.sync_action.setVisible(not running)
        # Ensure context menu is non-empty and visible
        self.setToolTip("Study Session Manager")
    
    def start_session(self):
        if self.session.is_running:
            self.show_notification("⚠️  Session Active", "End current session first", 3000); return
        # Auto-use last profile if set, otherwise prompt
        if self.last_profile:
            prof = self.api.db.get_profile(self.last_profile)
            if prof:
                self.current_location = prof.get('location', '')
                self.current_equipment = prof.get('equipment', '')
            else:
                # Profile was deleted, clear it
                self.last_profile = ""
                self.update_profile_display()
        # If no profile set, use current location/equipment (which may be empty)
        self.session.start();
        # Log locally only; no API call during session
        self.api.db.log_event(self.session.id, 'start', {})
        profile_info = f" ({self.last_profile})" if self.last_profile else ""
        self.show_notification("🎯 Session Started", f"Focus time activated!{profile_info}", 2000)
    
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
        # Toggle visibility of Sync vs Change Profile
        if hasattr(self, 'change_profile_action') and self.change_profile_action:
            self.change_profile_action.setVisible(running)
        if hasattr(self, 'sync_action') and self.sync_action:
            self.sync_action.setVisible(not running)
    
    def show_notification(self, title, message, duration=2000):
        self.showMessage(title, message, QSystemTrayIcon.Information, duration)
    
    def change_profile(self):
        """Allow user to select/edit a profile from the tray menu"""
        env_dialog = EnvironmentDialog(None, db=self.api.db, title="Select/Edit Profile", label="Choose or modify a profile")
        if env_dialog.exec_() != env_dialog.Accepted:
            return
        loc, eq = env_dialog.get_result()
        
        # Get the selected profile name if one was loaded
        profile_name = env_dialog.profile_combo.currentText() if env_dialog.profile_combo.currentText() else ""
        
        self.current_location = loc
        self.current_equipment = eq
        self.last_profile = profile_name
        self._save_last_profile()
        self.update_profile_display()
        self.show_notification("📋 Profile Updated", profile_name if profile_name else "Custom settings", 2000)
    
    def update_profile_display(self):
        """Update the profile action text in the menu"""
        if self.profile_action:
            display = self.last_profile if self.last_profile else "None"
            self.profile_action.setText(f"Profile: {display}")
    
    def _load_last_profile(self):
        """Load last used profile from persistent storage"""
        last_profile = self.api.db.get_setting('last_profile', '')
        if last_profile:
            prof = self.api.db.get_profile(last_profile)
            if prof:
                self.last_profile = last_profile
                self.current_location = prof.get('location', '')
                self.current_equipment = prof.get('equipment', '')
                logger.info(f"Loaded last profile: {last_profile}")
            else:
                logger.info(f"Last profile '{last_profile}' not found, cleared")
    
    def _save_last_profile(self):
        """Save last used profile to persistent storage"""
        self.api.db.set_setting('last_profile', self.last_profile)
        logger.info(f"Saved last profile: {self.last_profile or '(none)'}")
    
    def quit_app(self):
        self.hide(); self.app.quit()

    def change_profile_during_session(self):
        """Change profile during an active session - splits the session"""
        if not self.session.is_running:
            # Not running, just use the regular change_profile
            self.change_profile()
            return
        
        profiles = self.api.db.get_profiles()
        if not profiles:
            self.show_notification("📋 No Profiles", "Create profiles in Settings first", 2000)
            return
        
        profile_names = [p['name'] for p in profiles]
        dialog = SelectDialog(None, "Change Profile", "Select new profile (will split session):", profile_names)
        if dialog.exec_() != dialog.Accepted:
            return
        
        selected = dialog.get_value()
        if not selected:
            return
        
        prof = self.api.db.get_profile(selected)
        if not prof:
            return
        
        new_loc = prof.get('location', '')
        new_eq = prof.get('equipment', '')
        
        reply = QMessageBox.question(None,
                                     "Split Session?",
                                     f"Changing to profile '{selected}' will end the current session and start a new one. Continue?",
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
        auto_note = f"continuing session {old_id}; profile changed to {selected}"
        # End and persist old session with old env
        try:
            self.session.end()
        except Exception:
            pass
        self.api.db.save_session(self.session, auto_note, location=self.current_location, equipment=self.current_equipment)
        
        # Start a fresh session with new profile
        self.last_profile = selected
        self.current_location = new_loc
        self.current_equipment = new_eq
        self._save_last_profile()
        self.update_profile_display()
        self.session = StudySession(); self.session.status_changed.connect(self.on_session_status_changed)
        self.session.start()
        self.api.db.log_event(self.session.id, 'start', {})
        self.show_notification("📋 Profile Changed", f"New session started with {selected}", 3000)

    def open_settings(self):
        dlg = SettingsDialog(None, db=self.api.db, title="Settings")
        if dlg.exec_() == dlg.Accepted:
            self.show_notification("⚙️  Settings Saved", "Catalogs updated", 2000)
