#!/usr/bin/env python3
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, QPushButton, QComboBox, QLineEdit, QListWidget, QListWidgetItem, QTabWidget, QWidget, QMessageBox, QInputDialog
from PyQt5.QtCore import Qt
from db import SessionDatabase
from utils import check_connectivity

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


class EnvironmentDialog(QDialog):
    def __init__(self, parent=None, db: SessionDatabase = None, title="Environment", label="Choose location and equipment"):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(420)
        self.db = db or SessionDatabase()

        layout = QVBoxLayout(); layout.setSpacing(10); layout.setContentsMargins(16, 16, 16, 16)
        layout.addWidget(QLabel(label))

        # Connectivity status
        self.conn_label = QLabel("Checking connectivity…")
        layout.addWidget(self.conn_label)
        self._update_connectivity_label()

        # Profiles row
        prof_row = QHBoxLayout(); prof_row.setSpacing(8)
        prof_row.addWidget(QLabel("Profile:"))
        self.profile_combo = QComboBox(); self._reload_profiles()
        prof_row.addWidget(self.profile_combo, 1)
        load_btn = QPushButton("Load")
        save_btn = QPushButton("Save")
        del_btn = QPushButton("Delete")
        load_btn.clicked.connect(self._load_profile)
        save_btn.clicked.connect(self._save_profile)
        del_btn.clicked.connect(self._delete_profile)
        prof_row.addWidget(load_btn); prof_row.addWidget(save_btn); prof_row.addWidget(del_btn)
        layout.addLayout(prof_row)

        # Location row
        loc_row = QHBoxLayout(); loc_row.setSpacing(8)
        loc_row.addWidget(QLabel("Location:"))
        self.location_combo = QComboBox(); self.location_combo.setEditable(True)
        self._reload_locations()
        loc_row.addWidget(self.location_combo, 1)
        layout.addLayout(loc_row)

        # Equipment check-list
        layout.addWidget(QLabel("Equipment:"))
        self.equipment_list = QListWidget(); self._reload_equipment()
        self.equipment_list.setMinimumHeight(140)
        layout.addWidget(self.equipment_list)
        # Add equipment row
        add_row = QHBoxLayout(); add_row.setSpacing(8)
        self.new_equipment_input = QLineEdit(); self.new_equipment_input.setPlaceholderText("Add equipment and press +")
        add_btn = QPushButton("+")
        add_btn.setFixedWidth(32)
        add_btn.clicked.connect(self._add_equipment)
        add_row.addWidget(self.new_equipment_input, 1)
        add_row.addWidget(add_btn)
        layout.addLayout(add_row)

        # Buttons
        btns = QHBoxLayout(); btns.addStretch()
        ok_btn = QPushButton("OK"); ok_btn.setDefault(True); ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel"); cancel_btn.clicked.connect(self.reject)
        btns.addWidget(ok_btn); btns.addWidget(cancel_btn); layout.addLayout(btns)

        self.setLayout(layout)

    def _update_connectivity_label(self):
        reachable, latency = check_connectivity()
        if reachable:
            self.conn_label.setText(f"Online ✅ ({latency:.0f} ms)")
        else:
            self.conn_label.setText("Offline ⚠️")

    def _reload_profiles(self):
        self.profile_combo.clear()
        profiles = self.db.get_profiles()
        self.profile_combo.addItem("")
        for p in profiles:
            self.profile_combo.addItem(p.get('name', ''))

    def _reload_locations(self):
        self.location_combo.clear()
        locs = self.db.get_location_catalog()
        if not locs:
            locs = ["home", "class", "transports"]
        self.location_combo.addItems(locs)

    def _load_profile(self):
        name = self.profile_combo.currentText().strip()
        if not name:
            return
        prof = self.db.get_profile(name)
        if not prof:
            return
        loc = prof.get('location', '') or ''
        eq = prof.get('equipment', '') or ''
        # Ensure location present in combo
        if loc and loc not in [self.location_combo.itemText(i) for i in range(self.location_combo.count())]:
            self.location_combo.addItem(loc)
        if loc:
            self.location_combo.setCurrentText(loc)
        # Select matching equipment items
        wanted = {s.strip() for s in eq.split(',') if s.strip()}
        # Ensure all wanted items exist in list
        existing = {self.equipment_list.item(i).text(): i for i in range(self.equipment_list.count())}
        for name in wanted:
            if name not in existing:
                self._add_equipment_to_list(name, checked=True, persist=True)
        # Now set checks
        for i in range(self.equipment_list.count()):
            item = self.equipment_list.item(i)
            item.setCheckState(Qt.Checked if item.text() in wanted else Qt.Unchecked)

    def _save_profile(self):
        name = self.profile_combo.currentText().strip()
        if not name:
            return
        loc = self.location_combo.currentText().strip()
        eq_list = self._selected_equipment()
        eq = ", ".join(eq_list)
        self.db.save_profile(name, loc, eq)
        # Persist new location in catalog if new
        if loc:
            self.db.add_location(loc)
        self._reload_profiles()

    def _delete_profile(self):
        name = self.profile_combo.currentText().strip()
        if not name:
            return
        self.db.delete_profile(name)
        self._reload_profiles()

    def get_result(self):
        loc = self.location_combo.currentText().strip()
        eq_list = self._selected_equipment()
        eq = ", ".join(eq_list)
        # Persist new location in catalog if new
        if loc:
            self.db.add_location(loc)
        # Optionally add equipment items to catalog for future use
        for item in eq_list:
            self.db.add_equipment(item)
        return loc, eq

    def _reload_equipment(self):
        self.equipment_list.clear()
        for name in self.db.get_equipment_catalog():
            self._add_equipment_to_list(name, checked=False, persist=False)

    def _add_equipment_to_list(self, name: str, checked: bool = True, persist: bool = False):
        name = (name or '').strip()
        if not name:
            return
        # Avoid duplicates in UI
        for i in range(self.equipment_list.count()):
            if self.equipment_list.item(i).text() == name:
                # If exists, just ensure checked if requested
                if checked:
                    self.equipment_list.item(i).setCheckState(Qt.Checked)
                return
        item = QListWidgetItem(name)
        item.setFlags(item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable)
        item.setCheckState(Qt.Checked if checked else Qt.Unchecked)
        self.equipment_list.addItem(item)
        if persist:
            self.db.add_equipment(name)

    def _add_equipment(self):
        name = self.new_equipment_input.text().strip()
        if not name:
            return
        # Persist to catalog and add to list
        self.db.add_equipment(name)
        self._add_equipment_to_list(name, checked=True, persist=False)
        self.new_equipment_input.clear()

    def _selected_equipment(self):
        result = []
        for i in range(self.equipment_list.count()):
            item = self.equipment_list.item(i)
            if item.checkState() == Qt.Checked:
                result.append(item.text())
        return result


class SettingsDialog(QDialog):
    def __init__(self, parent=None, db: SessionDatabase = None, title="Settings"):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(550)
        self.setMinimumHeight(450)
        self.db = db or SessionDatabase()

        layout = QVBoxLayout(); layout.setSpacing(10); layout.setContentsMargins(16, 16, 16, 16)

        # Tabbed interface
        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_profiles_tab(), "Profiles")
        self.tabs.addTab(self._build_locations_tab(), "Locations")
        self.tabs.addTab(self._build_equipment_tab(), "Equipment")
        layout.addWidget(self.tabs)

        # Buttons
        btns = QHBoxLayout(); btns.addStretch()
        ok_btn = QPushButton("Close"); ok_btn.setDefault(True); ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel"); cancel_btn.clicked.connect(self.reject)
        btns.addWidget(ok_btn); btns.addWidget(cancel_btn); layout.addLayout(btns)
        self.setLayout(layout)

    def _build_profiles_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(); layout.setSpacing(10); layout.setContentsMargins(10, 10, 10, 10)
        layout.addWidget(QLabel("Manage environment profiles:"))
        
        self.profiles_list = QListWidget(); self.profiles_list.setMinimumHeight(200)
        self._reload_profiles_list()
        layout.addWidget(self.profiles_list)
        
        btn_row = QHBoxLayout(); btn_row.setSpacing(8)
        create_btn = QPushButton("Create New"); create_btn.clicked.connect(self._create_new_profile)
        edit_btn = QPushButton("Edit"); edit_btn.clicked.connect(self._edit_profile)
        rename_btn = QPushButton("Rename"); rename_btn.clicked.connect(self._rename_profile)
        delete_btn = QPushButton("Delete"); delete_btn.clicked.connect(self._delete_profile_from_list)
        btn_row.addWidget(create_btn); btn_row.addWidget(edit_btn); btn_row.addWidget(rename_btn); btn_row.addWidget(delete_btn)
        layout.addLayout(btn_row)
        
        layout.addStretch()
        tab.setLayout(layout)
        return tab

    def _build_locations_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(); layout.setSpacing(10); layout.setContentsMargins(10, 10, 10, 10)
        layout.addWidget(QLabel("Manage location catalog:"))
        
        self._orig_locations = set(self.db.get_location_catalog())
        self.locations_list = QListWidget(); self.locations_list.setMinimumHeight(200)
        for loc in sorted(self._orig_locations):
            self._add_list_item(self.locations_list, loc)
        layout.addWidget(self.locations_list)
        
        loc_row = QHBoxLayout(); loc_row.setSpacing(8)
        self.new_location_input = QLineEdit(); self.new_location_input.setPlaceholderText("Add location and press +")
        loc_add_btn = QPushButton("+"); loc_add_btn.setFixedWidth(32); loc_add_btn.clicked.connect(self._add_location)
        loc_del_btn = QPushButton("Remove Selected"); loc_del_btn.clicked.connect(self._remove_selected_locations)
        loc_row.addWidget(self.new_location_input, 1); loc_row.addWidget(loc_add_btn); loc_row.addWidget(loc_del_btn)
        layout.addLayout(loc_row)
        
        layout.addStretch()
        tab.setLayout(layout)
        return tab

    def _build_equipment_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(); layout.setSpacing(10); layout.setContentsMargins(10, 10, 10, 10)
        layout.addWidget(QLabel("Manage equipment catalog:"))
        
        self._orig_equipment = set(self.db.get_equipment_catalog())
        self.equipment_list2 = QListWidget(); self.equipment_list2.setMinimumHeight(200)
        for eq in sorted(self._orig_equipment):
            self._add_list_item(self.equipment_list2, eq)
        layout.addWidget(self.equipment_list2)
        
        eq_row = QHBoxLayout(); eq_row.setSpacing(8)
        self.new_equipment_input2 = QLineEdit(); self.new_equipment_input2.setPlaceholderText("Add equipment and press +")
        eq_add_btn = QPushButton("+"); eq_add_btn.setFixedWidth(32); eq_add_btn.clicked.connect(self._add_equipment2)
        eq_del_btn = QPushButton("Remove Selected"); eq_del_btn.clicked.connect(self._remove_selected_equipment)
        eq_row.addWidget(self.new_equipment_input2, 1); eq_row.addWidget(eq_add_btn); eq_row.addWidget(eq_del_btn)
        layout.addLayout(eq_row)
        
        layout.addStretch()
        tab.setLayout(layout)
        return tab

    def _reload_profiles_list(self):
        self.profiles_list.clear()
        for prof in self.db.get_profiles():
            name = prof.get('name', '')
            if name:
                self.profiles_list.addItem(QListWidgetItem(name))

    def _create_new_profile(self):
        name, ok = QInputDialog.getText(self, "Create Profile", "Profile name:")
        if not ok or not name.strip():
            return
        name = name.strip()
        # Check if exists
        if self.db.get_profile(name):
            QMessageBox.warning(self, "Profile Exists", f"A profile named '{name}' already exists.")
            return
        # Create with empty environment
        self.db.save_profile(name, location="", equipment="")
        self._reload_profiles_list()
        QMessageBox.information(self, "Profile Created", f"Profile '{name}' created. Click 'Edit' to set location and equipment.")

    def _edit_profile(self):
        selected = self.profiles_list.selectedItems()
        if not selected:
            QMessageBox.information(self, "No Selection", "Select a profile to edit.")
            return
        name = selected[0].text()
        prof = self.db.get_profile(name)
        if not prof:
            return
        
        # Open a mini environment editor
        dlg = ProfileEditDialog(self, db=self.db, profile_name=name, 
                                location=prof.get('location', ''), 
                                equipment=prof.get('equipment', ''))
        if dlg.exec_() == dlg.Accepted:
            loc, eq = dlg.get_result()
            self.db.save_profile(name, loc, eq)
            QMessageBox.information(self, "Profile Updated", f"Profile '{name}' saved.")


    def _rename_profile(self):
        selected = self.profiles_list.selectedItems()
        if not selected:
            return
        old_name = selected[0].text()
        new_name, ok = QInputDialog.getText(self, "Rename Profile", f"New name for '{old_name}':")
        if ok and new_name.strip():
            self.db.rename_profile(old_name, new_name.strip())
            self._reload_profiles_list()

    def _delete_profile_from_list(self):
        selected = self.profiles_list.selectedItems()
        if not selected:
            return
        name = selected[0].text()
        self.db.delete_profile(name)
        self._reload_profiles_list()


    def _add_list_item(self, widget: QListWidget, text: str):
        text = (text or '').strip()
        if not text:
            return
        # Avoid duplicates
        for i in range(widget.count()):
            if widget.item(i).text() == text:
                return
        widget.addItem(QListWidgetItem(text))

    def _add_location(self):
        name = self.new_location_input.text().strip()
        if not name:
            return
        self._add_list_item(self.locations_list, name)
        self.new_location_input.clear()

    def _add_equipment2(self):
        name = self.new_equipment_input2.text().strip()
        if not name:
            return
        self._add_list_item(self.equipment_list2, name)
        self.new_equipment_input2.clear()

    def _remove_selected_locations(self):
        for item in self.locations_list.selectedItems():
            self.locations_list.takeItem(self.locations_list.row(item))

    def _remove_selected_equipment(self):
        for item in self.equipment_list2.selectedItems():
            self.equipment_list2.takeItem(self.equipment_list2.row(item))

    def accept(self):
        # Save diffs for locations and equipment on close
        final_locations = {self.locations_list.item(i).text() for i in range(self.locations_list.count())}
        final_equipment = {self.equipment_list2.item(i).text() for i in range(self.equipment_list2.count())}

        # Compute diffs
        to_add_loc = final_locations - self._orig_locations
        to_remove_loc = self._orig_locations - final_locations
        to_add_eq = final_equipment - self._orig_equipment
        to_remove_eq = self._orig_equipment - final_equipment

        # Apply
        for n in sorted(to_add_loc):
            self.db.add_location(n)
        for n in sorted(to_remove_loc):
            self.db.remove_location(n)
        for n in sorted(to_add_eq):
            self.db.add_equipment(n)
        for n in sorted(to_remove_eq):
            self.db.remove_equipment(n)

        super().accept()


class ProfileEditDialog(QDialog):
    """Mini dialog to edit a profile's location and equipment."""
    def __init__(self, parent=None, db: SessionDatabase = None, profile_name: str = "", location: str = "", equipment: str = ""):
        super().__init__(parent)
        self.setWindowTitle(f"Edit Profile: {profile_name}")
        self.setMinimumWidth(450)
        self.db = db or SessionDatabase()
        
        layout = QVBoxLayout(); layout.setSpacing(10); layout.setContentsMargins(16, 16, 16, 16)
        
        # Location
        layout.addWidget(QLabel("Location:"))
        self.location_combo = QComboBox(); self.location_combo.setEditable(True)
        locs = self.db.get_location_catalog()
        if locs:
            self.location_combo.addItems(locs)
        if location:
            self.location_combo.setCurrentText(location)
        layout.addWidget(self.location_combo)
        
        # Equipment (checkboxes)
        layout.addWidget(QLabel("Equipment:"))
        self.equipment_list = QListWidget(); self.equipment_list.setMinimumHeight(150)
        self._load_equipment(equipment)
        layout.addWidget(self.equipment_list)
        
        # Add equipment row
        add_row = QHBoxLayout(); add_row.setSpacing(8)
        self.new_equipment_input = QLineEdit(); self.new_equipment_input.setPlaceholderText("Add equipment and press +")
        add_btn = QPushButton("+"); add_btn.setFixedWidth(32); add_btn.clicked.connect(self._add_equipment)
        add_row.addWidget(self.new_equipment_input, 1); add_row.addWidget(add_btn)
        layout.addLayout(add_row)
        
        # Buttons
        btns = QHBoxLayout(); btns.addStretch()
        ok_btn = QPushButton("Save"); ok_btn.setDefault(True); ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel"); cancel_btn.clicked.connect(self.reject)
        btns.addWidget(ok_btn); btns.addWidget(cancel_btn)
        layout.addLayout(btns)
        
        self.setLayout(layout)
    
    def _load_equipment(self, equipment_str: str):
        catalog = self.db.get_equipment_catalog()
        wanted = {s.strip() for s in equipment_str.split(',') if s.strip()}
        
        # Show all catalog items
        for eq in catalog:
            item = QListWidgetItem(eq)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            item.setCheckState(Qt.Checked if eq in wanted else Qt.Unchecked)
            self.equipment_list.addItem(item)
        
        # Add any wanted items not in catalog
        for eq in wanted:
            if eq not in catalog:
                item = QListWidgetItem(eq)
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                item.setCheckState(Qt.Checked)
                self.equipment_list.addItem(item)
    
    def _add_equipment(self):
        name = self.new_equipment_input.text().strip()
        if not name:
            return
        # Add to catalog
        self.db.add_equipment(name)
        # Add to list if not present
        for i in range(self.equipment_list.count()):
            if self.equipment_list.item(i).text() == name:
                self.equipment_list.item(i).setCheckState(Qt.Checked)
                self.new_equipment_input.clear()
                return
        item = QListWidgetItem(name)
        item.setFlags(item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable)
        item.setCheckState(Qt.Checked)
        self.equipment_list.addItem(item)
        self.new_equipment_input.clear()
    
    def get_result(self):
        loc = self.location_combo.currentText().strip()
        selected_eq = []
        for i in range(self.equipment_list.count()):
            item = self.equipment_list.item(i)
            if item.checkState() == Qt.Checked:
                selected_eq.append(item.text())
        eq = ", ".join(selected_eq)
        # Persist new location if needed
        if loc:
            self.db.add_location(loc)
        return loc, eq
