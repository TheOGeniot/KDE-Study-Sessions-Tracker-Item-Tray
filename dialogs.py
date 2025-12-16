#!/usr/bin/env python3
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, QPushButton, QComboBox, QLineEdit

class InputDialog(QDialog):
    def __init__(self, parent=None, title="Input", label="Enter text:", multiline=True):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(400)
        # Use native system theme - no custom styling
        layout = QVBoxLayout()
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)
        
        title_label = QLabel(label)
        layout.addWidget(title_label)
        
        if multiline:
            self.text_input = QTextEdit()
            self.text_input.setMinimumHeight(100)
        else:
            self.text_input = QLineEdit()
        self.text_input.setPlaceholderText("(optional)")
        layout.addWidget(self.text_input)
        
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        ok_btn = QPushButton("OK")
        ok_btn.setDefault(True)
        ok_btn.clicked.connect(self.accept)
        button_layout.addWidget(ok_btn)
        cancel_btn = QPushButton("Cancel")
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
        self.setMinimumWidth(350)
        # Use native system theme - no custom styling
        layout = QVBoxLayout()
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)
        
        label_widget = QLabel(label)
        layout.addWidget(label_widget)
        
        self.combo = QComboBox()
        if options:
            self.combo.addItems(options)
        layout.addWidget(self.combo)
        
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        ok_btn = QPushButton("OK")
        ok_btn.setDefault(True)
        ok_btn.clicked.connect(self.accept)
        button_layout.addWidget(ok_btn)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def get_value(self):
        return self.combo.currentText()
