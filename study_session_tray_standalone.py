#!/usr/bin/env python3
"""
Study Session Manager — Main Entrypoint
Clean, modular app using PyQt5 system tray.

Project structure:
- models.py: Pause, PauseManager, StudySession
- db.py: SessionDatabase
- api.py: SessionAPIManager
- dialogs.py: InputDialog, SelectDialog
- tray.py: StudySessionTray (UI and actions)
- study_session_tray_standalone.py: Entrypoint (this file)
"""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv
from PyQt5.QtWidgets import QApplication, QSystemTrayIcon, QWidget, QVBoxLayout, QPushButton, QLabel

from tray import StudySessionTray


def main():
    """Main entry point: load env, start Qt app, show tray"""
    load_dotenv(dotenv_path=Path(__file__).parent / '.env')
    app = QApplication(sys.argv)
    app.setApplicationName("Study Session Manager")
    app.setApplicationVersion("1.0.0")
    app.setQuitOnLastWindowClosed(False)

    n8n_url = os.getenv('N8N_BASE_URL')
    print(f"✅ N8N configured: {n8n_url}") if n8n_url else print("⚠️  N8N_BASE_URL not set (using local-only mode)")

    # Ensure system tray is available
    tray = None
    if not QSystemTrayIcon.isSystemTrayAvailable():
        print("❌ System tray not available on this desktop environment. Launching fallback window.")
        # Fallback window to access the same menu actions
        tray = StudySessionTray(app)
        class FallbackWindow(QWidget):
            def __init__(self, tray_ref):
                super().__init__()
                self.tray_ref = tray_ref
                self.setWindowTitle("Study Session Manager (Fallback)")
                layout = QVBoxLayout()
                self.info = QLabel("System tray unavailable. Use this window to access the menu.")
                layout.addWidget(self.info)
                btn = QPushButton("Open Menu")
                btn.clicked.connect(self.open_menu)
                layout.addWidget(btn)
                self.setLayout(layout)
            def open_menu(self):
                if self.tray_ref and self.tray_ref.menu:
                    # Show menu centered over the window
                    self.tray_ref.menu.exec_(self.mapToGlobal(self.rect().center()))
        fallback = FallbackWindow(tray)
        fallback.show()
    else:
        tray = StudySessionTray(app)
        tray.show()
        tray.setVisible(True)

    print("\n🚀 Study Session Manager started")
    print("📍 Local storage: ~/.local/share/study-session/sessions.db")
    print("💡 Right-click the tray icon to access menu")
    print("🔧 Features: Multiple pauses per session with reasons, mood tracking, N8N sync\n")

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
