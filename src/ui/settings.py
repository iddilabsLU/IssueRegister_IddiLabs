"""Settings view for configuration and user management."""

from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QGroupBox, QLineEdit, QPushButton, QLabel, QCheckBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QFileDialog, QDialog, QComboBox, QListWidget, QAbstractItemView,
    QScrollArea, QFrame
)
from PySide6.QtCore import Qt

from src.database.models import User, UserRole
from src.database import queries
from src.database.connection import DatabaseConnection
from src.services.auth import get_auth_service, AuthService
from src.services.permissions import get_permission_service
from src.services.export import get_export_service


class SettingsView(QWidget):
    """
    Settings view with database config, auth settings, and user management.

    Sections:
    - Database Configuration
    - Authentication Settings (Admin only)
    - User Management (Admin only)
    - Data Management (Backup/Import)
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self._auth = get_auth_service()
        self._permissions = get_permission_service()
        self._export = get_export_service()
        self._user: Optional[User] = None

        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        """Set up the settings UI."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        content = QWidget()
        main_layout = QVBoxLayout(content)
        main_layout.setSpacing(24)
        main_layout.setContentsMargins(24, 24, 24, 24)

        # Header
        header = QLabel("Settings")
        header.setProperty("heading", True)
        main_layout.addWidget(header)

        # Database Configuration
        db_group = QGroupBox("Database Configuration")
        db_layout = QFormLayout(db_group)
        db_layout.setSpacing(12)

        db_path_layout = QHBoxLayout()
        self._db_path_edit = QLineEdit()
        self._db_path_edit.setReadOnly(True)
        db_path_layout.addWidget(self._db_path_edit, 1)

        self._browse_btn = QPushButton("Browse...")
        db_path_layout.addWidget(self._browse_btn)

        db_layout.addRow("Database Path:", db_path_layout)

        db_status_layout = QHBoxLayout()
        self._db_status_label = QLabel("Connected")
        self._db_status_label.setStyleSheet("color: #059669;")
        db_status_layout.addWidget(self._db_status_label)
        db_status_layout.addStretch()
        db_layout.addRow("Status:", db_status_layout)

        main_layout.addWidget(db_group)

        # Authentication Settings
        self._auth_group = QGroupBox("Authentication Settings")
        auth_layout = QVBoxLayout(self._auth_group)

        self._auth_checkbox = QCheckBox("Enable Authentication")
        self._auth_checkbox.setToolTip(
            "When enabled, users must log in with username and password.\n"
            "When disabled, all users have administrator access."
        )
        auth_layout.addWidget(self._auth_checkbox)

        auth_note = QLabel(
            "Note: When authentication is first enabled, the default admin account\n"
            "(username: admin, password: admin) becomes active."
        )
        auth_note.setProperty("muted", True)
        auth_layout.addWidget(auth_note)

        main_layout.addWidget(self._auth_group)

        # User Management
        self._user_group = QGroupBox("User Management")
        user_layout = QVBoxLayout(self._user_group)

        # User table
        self._user_table = QTableWidget()
        self._user_table.setColumnCount(4)
        self._user_table.setHorizontalHeaderLabels(["ID", "Username", "Role", "Departments"])
        self._user_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._user_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._user_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._user_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self._user_table.setMaximumHeight(200)
        user_layout.addWidget(self._user_table)

        # User action buttons
        user_btn_layout = QHBoxLayout()
        self._add_user_btn = QPushButton("Add User")
        user_btn_layout.addWidget(self._add_user_btn)

        self._edit_user_btn = QPushButton("Edit User")
        user_btn_layout.addWidget(self._edit_user_btn)

        self._delete_user_btn = QPushButton("Delete User")
        self._delete_user_btn.setProperty("danger", True)
        user_btn_layout.addWidget(self._delete_user_btn)

        user_btn_layout.addStretch()
        user_layout.addLayout(user_btn_layout)

        main_layout.addWidget(self._user_group)

        # Data Management
        data_group = QGroupBox("Data Management")
        data_layout = QVBoxLayout(data_group)

        # Export backup section
        export_layout = QHBoxLayout()
        export_label = QLabel("Export backup of all issues:")
        export_layout.addWidget(export_label)
        export_layout.addStretch()
        self._export_backup_btn = QPushButton("Export Backup")
        export_layout.addWidget(self._export_backup_btn)
        data_layout.addLayout(export_layout)

        # Export Users section (Admin only)
        self._export_users_frame = QFrame()
        export_users_layout = QHBoxLayout(self._export_users_frame)
        export_users_layout.setContentsMargins(0, 0, 0, 0)
        export_users_label = QLabel("Export user list to Excel:")
        export_users_layout.addWidget(export_users_label)
        export_users_layout.addStretch()
        self._export_users_btn = QPushButton("Export Users")
        export_users_layout.addWidget(self._export_users_btn)
        data_layout.addWidget(self._export_users_frame)

        # Export Audit Log section (Admin + Editor)
        self._export_audit_frame = QFrame()
        export_audit_layout = QHBoxLayout(self._export_audit_frame)
        export_audit_layout.setContentsMargins(0, 0, 0, 0)
        export_audit_label = QLabel("Export audit log to Excel:")
        export_audit_layout.addWidget(export_audit_label)
        export_audit_layout.addStretch()
        self._export_audit_btn = QPushButton("Export Audit Log")
        export_audit_layout.addWidget(self._export_audit_btn)
        data_layout.addWidget(self._export_audit_frame)

        # Import section (Admin only)
        self._import_frame = QFrame()
        import_layout = QHBoxLayout(self._import_frame)
        import_layout.setContentsMargins(0, 0, 0, 0)
        import_label = QLabel("Import backup (overwrites current data):")
        import_layout.addWidget(import_label)
        import_layout.addStretch()
        self._import_backup_btn = QPushButton("Import Backup")
        import_layout.addWidget(self._import_backup_btn)
        data_layout.addWidget(self._import_frame)

        # Bulk import section
        self._bulk_frame = QFrame()
        bulk_layout = QHBoxLayout(self._bulk_frame)
        bulk_layout.setContentsMargins(0, 0, 0, 0)
        bulk_label = QLabel("Bulk import issues from Excel:")
        bulk_layout.addWidget(bulk_label)
        bulk_layout.addStretch()
        self._download_template_btn = QPushButton("Download Template")
        bulk_layout.addWidget(self._download_template_btn)
        self._bulk_import_btn = QPushButton("Import Excel")
        bulk_layout.addWidget(self._bulk_import_btn)
        data_layout.addWidget(self._bulk_frame)

        main_layout.addWidget(data_group)

        main_layout.addStretch()

        scroll.setWidget(content)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(scroll)

    def _connect_signals(self):
        """Connect UI signals."""
        self._browse_btn.clicked.connect(self._on_browse_database)
        self._auth_checkbox.stateChanged.connect(self._on_auth_changed)
        self._add_user_btn.clicked.connect(self._on_add_user)
        self._edit_user_btn.clicked.connect(self._on_edit_user)
        self._delete_user_btn.clicked.connect(self._on_delete_user)
        self._export_backup_btn.clicked.connect(self._on_export_backup)
        self._export_users_btn.clicked.connect(self._on_export_users)
        self._export_audit_btn.clicked.connect(self._on_export_audit_log)
        self._import_backup_btn.clicked.connect(self._on_import_backup)
        self._download_template_btn.clicked.connect(self._on_download_template)
        self._bulk_import_btn.clicked.connect(self._on_bulk_import)

    def set_user(self, user: User):
        """Set current user and update permissions."""
        self._user = user
        self._apply_permissions()
        self.refresh()

    def _apply_permissions(self):
        """Apply permission-based visibility."""
        if not self._user:
            return

        is_admin = self._permissions.can_manage_users(self._user)
        is_editor_or_admin = self._user.role in [UserRole.ADMINISTRATOR.value, UserRole.EDITOR.value]

        self._auth_group.setVisible(is_admin)
        self._user_group.setVisible(is_admin)
        self._import_frame.setVisible(is_admin)
        self._bulk_frame.setVisible(is_admin)
        self._browse_btn.setEnabled(is_admin)

        # Export Users - Admin only
        self._export_users_frame.setVisible(is_admin)

        # Export Audit Log - Admin + Editor
        self._export_audit_frame.setVisible(is_editor_or_admin)

    def refresh(self):
        """Refresh settings data."""
        # Update database path
        db = DatabaseConnection.get_instance()
        self._db_path_edit.setText(str(db.db_path))

        # Update auth checkbox
        self._auth_checkbox.blockSignals(True)
        self._auth_checkbox.setChecked(self._auth.is_auth_enabled)
        self._auth_checkbox.blockSignals(False)

        # Refresh user table
        self._refresh_user_table()

    def _refresh_user_table(self):
        """Refresh the user management table."""
        users = queries.list_users()

        self._user_table.setRowCount(len(users))
        for row, user in enumerate(users):
            self._user_table.setItem(row, 0, QTableWidgetItem(str(user.id)))
            self._user_table.setItem(row, 1, QTableWidgetItem(user.username))
            self._user_table.setItem(row, 2, QTableWidgetItem(user.role))
            self._user_table.setItem(row, 3, QTableWidgetItem(
                ", ".join(user.departments) if user.departments else "All"
            ))

    def _on_browse_database(self):
        """Browse for database file."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Select Database Location",
            "issue_register.db",
            "SQLite Database (*.db)"
        )

        if not file_path:
            return

        try:
            # Change database path
            DatabaseConnection.set_database_path(file_path)

            # Run migrations if new
            from src.database.migrations import run_migrations
            run_migrations()

            self._db_path_edit.setText(file_path)
            self._db_status_label.setText("Connected")
            self._db_status_label.setStyleSheet("color: #059669;")

            QMessageBox.information(
                self,
                "Database Changed",
                f"Successfully connected to database:\n{file_path}"
            )

        except Exception as e:
            QMessageBox.critical(
                self,
                "Database Error",
                f"Failed to connect to database:\n{str(e)}"
            )

    def _on_auth_changed(self, state):
        """Handle authentication enable/disable."""
        enable = state == Qt.CheckState.Checked.value

        if enable:
            reply = QMessageBox.question(
                self,
                "Enable Authentication",
                "Are you sure you want to enable authentication?\n\n"
                "The default admin account (admin/admin) will become active.\n"
                "All users will need to log in.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )

            if reply != QMessageBox.StandardButton.Yes:
                self._auth_checkbox.blockSignals(True)
                self._auth_checkbox.setChecked(False)
                self._auth_checkbox.blockSignals(False)
                return

        self._auth.enable_authentication(enable)

        QMessageBox.information(
            self,
            "Authentication Updated",
            f"Authentication has been {'enabled' if enable else 'disabled'}.\n"
            "Changes will take effect on next login."
        )

    def _on_add_user(self):
        """Open dialog to add new user."""
        dialog = UserDialog(parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._refresh_user_table()

    def _on_edit_user(self):
        """Edit selected user."""
        row = self._user_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "No Selection", "Please select a user to edit.")
            return

        user_id = int(self._user_table.item(row, 0).text())
        user = queries.get_user(user_id)

        if user:
            dialog = UserDialog(user=user, parent=self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self._refresh_user_table()

    def _on_delete_user(self):
        """Delete selected user."""
        row = self._user_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "No Selection", "Please select a user to delete.")
            return

        user_id = int(self._user_table.item(row, 0).text())
        username = self._user_table.item(row, 1).text()

        reply = QMessageBox.warning(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete user '{username}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            if self._auth.delete_user(user_id):
                self._refresh_user_table()
            else:
                QMessageBox.critical(
                    self,
                    "Delete Failed",
                    "Cannot delete the last administrator account."
                )

    def _on_export_backup(self):
        """Export database backup."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Backup",
            "issue_register_backup.db",
            "SQLite Database (*.db)"
        )

        if not file_path:
            return

        success, error = self._export.backup_database(file_path)

        if success:
            QMessageBox.information(
                self,
                "Backup Complete",
                f"Database backup saved to:\n{file_path}"
            )
        else:
            QMessageBox.critical(self, "Backup Failed", error)

    def _on_export_users(self):
        """Export users list to Excel."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Users",
            "users_export.xlsx",
            "Excel Files (*.xlsx)"
        )

        if not file_path:
            return

        success, error = self._export.export_users_to_excel(file_path)

        if success:
            users_count = len(queries.list_users())
            QMessageBox.information(
                self,
                "Export Complete",
                f"Successfully exported {users_count} users to:\n{file_path}"
            )
        else:
            QMessageBox.critical(self, "Export Failed", error)

    def _on_export_audit_log(self):
        """Export audit log to Excel."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Audit Log",
            "audit_log_export.xlsx",
            "Excel Files (*.xlsx)"
        )

        if not file_path:
            return

        success, error = self._export.export_audit_log(file_path)

        if success:
            QMessageBox.information(
                self,
                "Export Complete",
                f"Audit log exported to:\n{file_path}"
            )
        else:
            QMessageBox.critical(self, "Export Failed", error)

    def _on_import_backup(self):
        """Import database backup."""
        reply = QMessageBox.warning(
            self,
            "Confirm Import",
            "Importing a backup will OVERWRITE all current data.\n\n"
            "This action cannot be undone. Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Backup",
            "",
            "SQLite Database (*.db)"
        )

        if not file_path:
            return

        success, error = self._export.restore_database(file_path)

        if success:
            QMessageBox.information(
                self,
                "Import Complete",
                "Database restored successfully.\n"
                "Please restart the application."
            )
        else:
            QMessageBox.critical(self, "Import Failed", error)

    def _on_download_template(self):
        """Download import template."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Import Template",
            "issue_import_template.xlsx",
            "Excel Files (*.xlsx)"
        )

        if not file_path:
            return

        success, error = self._export.create_import_template(file_path)

        if success:
            QMessageBox.information(
                self,
                "Template Created",
                f"Import template saved to:\n{file_path}"
            )
        else:
            QMessageBox.critical(self, "Template Failed", error)

    def _on_bulk_import(self):
        """Bulk import issues from Excel."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Issues",
            "",
            "Excel Files (*.xlsx)"
        )

        if not file_path:
            return

        success_count, errors = self._export.import_issues_from_excel(file_path)

        message = f"Successfully imported {success_count} issues."
        if errors:
            message += f"\n\nErrors ({len(errors)}):\n" + "\n".join(errors[:10])
            if len(errors) > 10:
                message += f"\n... and {len(errors) - 10} more errors"

        QMessageBox.information(self, "Import Complete", message)


class UserDialog(QDialog):
    """Dialog for creating/editing users."""

    def __init__(self, user: Optional[User] = None, parent=None):
        super().__init__(parent)

        self._user = user
        self._is_new = user is None
        self._auth = get_auth_service()

        self._setup_ui()

        if user:
            self._load_user()

    def _setup_ui(self):
        """Set up dialog UI."""
        self.setWindowTitle("Add User" if self._is_new else "Edit User")
        self.setMinimumSize(450, 500)

        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        form = QFormLayout()
        form.setSpacing(12)

        self._username_edit = QLineEdit()
        form.addRow("Username:", self._username_edit)

        self._password_edit = QLineEdit()
        self._password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._password_edit.setPlaceholderText(
            "Enter password" if self._is_new else "Leave blank to keep current"
        )
        form.addRow("Password:", self._password_edit)

        self._role_combo = QComboBox()
        for role in UserRole.values():
            self._role_combo.addItem(role)
        self._role_combo.currentTextChanged.connect(self._on_role_changed)
        form.addRow("Role:", self._role_combo)

        layout.addLayout(form)

        # Departments (for Restricted/Viewer)
        self._dept_group = QGroupBox("Department Access")
        dept_layout = QVBoxLayout(self._dept_group)

        dept_note = QLabel("Select departments this user can access:")
        dept_note.setProperty("muted", True)
        dept_layout.addWidget(dept_note)

        self._dept_list = QListWidget()
        self._dept_list.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        self._dept_list.setMaximumHeight(100)

        # Load departments
        self._all_departments = []
        try:
            self._all_departments = queries.get_distinct_values("department")
            for dept in self._all_departments:
                self._dept_list.addItem(dept)
        except Exception:
            pass

        dept_layout.addWidget(self._dept_list)

        layout.addWidget(self._dept_group)

        # Editor department restrictions (two lists)
        self._editor_dept_group = QGroupBox("Editor Department Restrictions")
        editor_dept_layout = QVBoxLayout(self._editor_dept_group)

        # View departments
        view_label = QLabel("Departments this editor can VIEW:")
        view_label.setProperty("muted", True)
        editor_dept_layout.addWidget(view_label)

        self._view_dept_list = QListWidget()
        self._view_dept_list.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        self._view_dept_list.setMaximumHeight(80)
        for dept in self._all_departments:
            self._view_dept_list.addItem(dept)
        editor_dept_layout.addWidget(self._view_dept_list)

        # Edit departments
        edit_label = QLabel("Departments this editor can EDIT:")
        edit_label.setProperty("muted", True)
        editor_dept_layout.addWidget(edit_label)

        self._edit_dept_list = QListWidget()
        self._edit_dept_list.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        self._edit_dept_list.setMaximumHeight(80)
        for dept in self._all_departments:
            self._edit_dept_list.addItem(dept)
        editor_dept_layout.addWidget(self._edit_dept_list)

        edit_note = QLabel("Leave empty for unrestricted access to all departments.")
        edit_note.setProperty("muted", True)
        edit_note.setWordWrap(True)
        editor_dept_layout.addWidget(edit_note)

        layout.addWidget(self._editor_dept_group)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Save")
        save_btn.setProperty("primary", True)
        save_btn.clicked.connect(self._on_save)
        btn_layout.addWidget(save_btn)

        layout.addLayout(btn_layout)

        # Initial state
        self._on_role_changed(self._role_combo.currentText())

    def _load_user(self):
        """Load user data into form."""
        self._username_edit.setText(self._user.username)

        idx = self._role_combo.findText(self._user.role)
        if idx >= 0:
            self._role_combo.setCurrentIndex(idx)

        # Select departments for Restricted/Viewer
        for i in range(self._dept_list.count()):
            item = self._dept_list.item(i)
            if item.text() in self._user.departments:
                item.setSelected(True)

        # Select view/edit departments for Editor
        for i in range(self._view_dept_list.count()):
            item = self._view_dept_list.item(i)
            if item.text() in self._user.view_departments:
                item.setSelected(True)

        for i in range(self._edit_dept_list.count()):
            item = self._edit_dept_list.item(i)
            if item.text() in self._user.edit_departments:
                item.setSelected(True)

    def _on_role_changed(self, role: str):
        """Show/hide departments based on role."""
        # Restricted/Viewer: single department list
        show_restricted_depts = role in [UserRole.RESTRICTED.value, UserRole.VIEWER.value]
        self._dept_group.setVisible(show_restricted_depts)

        # Editor: two department lists (view + edit)
        show_editor_depts = role == UserRole.EDITOR.value
        self._editor_dept_group.setVisible(show_editor_depts)

    def _on_save(self):
        """Save user."""
        username = self._username_edit.text().strip()
        password = self._password_edit.text()
        role = self._role_combo.currentText()

        if not username:
            QMessageBox.warning(self, "Validation", "Username is required.")
            return

        if self._is_new and not password:
            QMessageBox.warning(self, "Validation", "Password is required for new users.")
            return

        # Get selected departments based on role
        departments = []
        view_departments = []
        edit_departments = []

        if role in [UserRole.RESTRICTED.value, UserRole.VIEWER.value]:
            departments = [
                self._dept_list.item(i).text()
                for i in range(self._dept_list.count())
                if self._dept_list.item(i).isSelected()
            ]
        elif role == UserRole.EDITOR.value:
            view_departments = [
                self._view_dept_list.item(i).text()
                for i in range(self._view_dept_list.count())
                if self._view_dept_list.item(i).isSelected()
            ]
            edit_departments = [
                self._edit_dept_list.item(i).text()
                for i in range(self._edit_dept_list.count())
                if self._edit_dept_list.item(i).isSelected()
            ]

        if self._is_new:
            user = self._auth.create_user(
                username, password, role, departments,
                view_departments=view_departments,
                edit_departments=edit_departments
            )
            if not user:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Username '{username}' already exists."
                )
                return
        else:
            user = self._auth.update_user(
                self._user.id,
                username=username,
                password=password if password else None,
                role=role,
                departments=departments,
                view_departments=view_departments,
                edit_departments=edit_departments
            )
            if not user:
                QMessageBox.critical(
                    self,
                    "Error",
                    "Failed to update user. Username may already exist."
                )
                return

        self.accept()
