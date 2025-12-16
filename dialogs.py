#!/usr/bin/env python3
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, QPushButton, QComboBox, QLineEdit

class InputDialog(QDialog):
    def __init__(self, parent=None, title="Input", label="Enter text:", multiline=True):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setGeometry(100, 100, 400, 250)
        self.setStyleSheet("""
            QDialog { background-color: #f5f5f5; border-radius: 8px; }
            QLabel { color: #1f2121; font-weight: bold; }
            QPushButton { background-color: #218091; color: white; border: none; border-radius: 4px; padding: 6px 12px; font-weight: bold; }
            QPushButton:hover { background-color: #1a6b7a; }
            QPushButton:pressed { background-color: #165960; }
        """)
        layout = QVBoxLayout(); layout.setSpacing(12); layout.setContentsMargins(16,16,16,16)
        title_label = QLabel(label)
        title_font = title_label.font(); title_font.setPointSize(10); title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)
        if multiline:
            self.text_input = QTextEdit(); self.text_input.setMinimumHeight(100)
        else:
            self.text_input = QLineEdit()
        self.text_input.setPlaceholderText("(optional)")
        layout.addWidget(self.text_input)
        button_layout = QHBoxLayout(); button_layout.addStretch()
        ok_btn = QPushButton("✓ OK"); ok_btn.setMinimumWidth(80); ok_btn.clicked.connect(self.accept)
        button_layout.addWidget(ok_btn)
        cancel_btn = QPushButton("✕ Cancel"); cancel_btn.setMinimumWidth(80)
        cancel_btn.setStyleSheet("""
            QPushButton { background-color: #c0152f; }
            QPushButton:hover { background-color: #a01229; }
        """)
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)
        self.setLayout(layout)
    def get_text(self):
        if hasattr(self.text_input, 'toPlainText'):
            return self.text_input.toPlainText().strip()
        else:
            return self.text_input.text().strip()

class SelectDialog(QDialog):
    def __init__(self, parent=None, title="Select", label="Choose:", options=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setGeometry(100, 100, 350, 180)
        self.setStyleSheet("""
            QDialog { background-color: #f5f5f5; }
            QLabel { color: #1f2121; font-weight: bold; }
            QComboBox { padding: 6px; border: 1px solid #ddd; border-radius: 4px; background-color: white; }
            QPushButton { background-color: #218091; color: white; border: none; border-radius: 4px; padding: 6px 12px; font-weight: bold; }
            QPushButton:hover { background-color: #1a6b7a; }
        """)
        layout = QVBoxLayout(); layout.setSpacing(12); layout.setContentsMargins(16,16,16,16)
        label_widget = QLabel(label); layout.addWidget(label_widget)
        self.combo = QComboBox();
        if options: self.combo.addItems(options)
        layout.addWidget(self.combo)
        button_layout = QHBoxLayout(); button_layout.addStretch()
        ok_btn = QPushButton("✓ OK"); ok_btn.clicked.connect(self.accept)
        button_layout.addWidget(ok_btn)
        cancel_btn = QPushButton("✕ Cancel")
        cancel_btn.setStyleSheet("""
            QPushButton { background-color: #c0152f; }
            QPushButton:hover { background-color: #a01229; }
        """)
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)
        self.setLayout(layout)
    def get_value(self):
        return self.combo.currentText()
