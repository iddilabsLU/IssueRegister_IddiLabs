"""Settings view for configuration and user management."""

from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QGroupBox, QLineEdit, QPushButton, QLabel, QCheckBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QFileDialog, QDialog, QComboBox, QAbstractItemView,
    QScrollArea, QFrame
)
from PySide6.QtCore import Qt

from src.database.models import User, UserRole
from src.ui.widgets.filter_panel import MultiSelectComboBox
from src.database import queries
from src.database.connection import DatabaseConnection
from src.services.auth import get_auth_service, AuthService
from src.services.permissions import get_permission_service
from src.services.export import get_export_service
from src.services.config import set_saved_database_path


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
        db_layout = QVBoxLayout(db_group)
        db_layout.setSpacing(12)

        # Current path display
        path_form = QFormLayout()
        self._db_path_edit = QLineEdit()
        self._db_path_edit.setReadOnly(True)
        path_form.addRow("Current Database:", self._db_path_edit)

        db_status_layout = QHBoxLayout()
        self._db_status_label = QLabel("Connected")
        self._db_status_label.setStyleSheet("color: #059669;")
        db_status_layout.addWidget(self._db_status_label)
        db_status_layout.addStretch()
        path_form.addRow("Status:", db_status_layout)

        db_layout.addLayout(path_form)

        # Database selection buttons
        db_btn_layout = QHBoxLayout()
        self._open_existing_btn = QPushButton("Open Existing Database")
        db_btn_layout.addWidget(self._open_existing_btn)

        self._create_new_btn = QPushButton("Create New Database")
        db_btn_layout.addWidget(self._create_new_btn)

        db_btn_layout.addStretch()
        db_layout.addLayout(db_btn_layout)

        main_layout.addWidget(db_group)

        # My Account Section (visible to all users)
        account_group = QGroupBox("My Account")
        account_layout = QVBoxLayout(account_group)

        # Current user info
        self._user_info_label = QLabel("Not logged in")
        account_layout.addWidget(self._user_info_label)

        # Change password button
        change_pw_layout = QHBoxLayout()
        change_pw_label = QLabel("Update your login password:")
        change_pw_layout.addWidget(change_pw_label)
        change_pw_layout.addStretch()
        self._change_password_btn = QPushButton("Change Password")
        change_pw_layout.addWidget(self._change_password_btn)
        account_layout.addLayout(change_pw_layout)

        main_layout.addWidget(account_group)

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

        # Master password change section
        master_pw_layout = QHBoxLayout()
        master_pw_label = QLabel("Master recovery password:")
        master_pw_layout.addWidget(master_pw_label)
        master_pw_layout.addStretch()
        self._change_master_pw_btn = QPushButton("Change Master Password")
        master_pw_layout.addWidget(self._change_master_pw_btn)
        auth_layout.addLayout(master_pw_layout)

        main_layout.addWidget(self._auth_group)

        # Data Management (includes User Management for admins)
        data_group = QGroupBox("Data Management")
        data_layout = QVBoxLayout(data_group)

        # Export backup section
        export_layout = QHBoxLayout()
        export_label = QLabel("Export backup (database + attachments):")
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
        import_label = QLabel("Import backup (overwrites database + attachments):")
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

        # User Management section (Admin only) - inside data management
        self._user_group = QFrame()
        user_layout = QVBoxLayout(self._user_group)
        user_layout.setContentsMargins(0, 12, 0, 0)

        # User management header with separator
        user_header = QLabel("User Management")
        user_header.setProperty("subheading", True)
        user_header.setStyleSheet("font-weight: bold; font-size: 14px; margin-top: 8px;")
        user_layout.addWidget(user_header)

        # User search
        search_layout = QHBoxLayout()
        search_label = QLabel("Search:")
        search_layout.addWidget(search_label)
        self._user_search_edit = QLineEdit()
        self._user_search_edit.setPlaceholderText("Search by username...")
        self._user_search_edit.setClearButtonEnabled(True)
        search_layout.addWidget(self._user_search_edit, 1)
        user_layout.addLayout(search_layout)

        # User table - now with more space (removed max height)
        self._user_table = QTableWidget()
        self._user_table.setColumnCount(5)
        self._user_table.setHorizontalHeaderLabels(
            ["ID", "Username", "Role", "Editor Rights", "Viewer Rights"]
        )
        self._user_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._user_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._user_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._user_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self._user_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self._user_table.setMinimumHeight(400)
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

        data_layout.addWidget(self._user_group)

        main_layout.addWidget(data_group)

        main_layout.addStretch()

        scroll.setWidget(content)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(scroll)

    def _connect_signals(self):
        """Connect UI signals."""
        self._open_existing_btn.clicked.connect(self._on_open_existing_database)
        self._create_new_btn.clicked.connect(self._on_create_new_database)
        self._change_password_btn.clicked.connect(self._on_change_password)
        self._auth_checkbox.stateChanged.connect(self._on_auth_changed)
        self._change_master_pw_btn.clicked.connect(self._on_change_master_password)
        self._user_search_edit.textChanged.connect(self._on_user_search_changed)
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
        self._update_user_info()
        self.refresh()

    def _update_user_info(self):
        """Update user info display."""
        if self._user:
            self._user_info_label.setText(
                f"Logged in as: {self._user.username} ({self._user.role})"
            )
        else:
            self._user_info_label.setText("Not logged in")

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
        # Database buttons are available to all users (for shared database scenarios)
        self._open_existing_btn.setEnabled(True)
        self._create_new_btn.setEnabled(True)

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
        """Refresh the user management table with optional search filter."""
        users = queries.list_users()

        # Apply search filter if search text exists
        search_text = self._user_search_edit.text().strip().lower()
        if search_text:
            users = [u for u in users if search_text in u.username.lower()]

        self._user_table.setRowCount(len(users))
        for row, user in enumerate(users):
            self._user_table.setItem(row, 0, QTableWidgetItem(str(user.id)))
            self._user_table.setItem(row, 1, QTableWidgetItem(user.username))
            self._user_table.setItem(row, 2, QTableWidgetItem(user.role))

            # Determine Editor Rights and Viewer Rights based on role
            if user.role == UserRole.ADMINISTRATOR.value:
                # Administrators have full access
                editor_rights = "All"
                viewer_rights = "All"
            elif user.role == UserRole.EDITOR.value:
                # Editors have separate edit and view department lists
                editor_rights = ", ".join(user.edit_departments) if user.edit_departments else "All"
                viewer_rights = ", ".join(user.view_departments) if user.view_departments else "All"
            elif user.role == UserRole.RESTRICTED.value:
                # Restricted users can edit in their assigned departments
                editor_rights = ", ".join(user.departments) if user.departments else "All"
                viewer_rights = ", ".join(user.departments) if user.departments else "All"
            else:
                # Viewers have no edit rights, only view rights
                editor_rights = "-"
                viewer_rights = ", ".join(user.departments) if user.departments else "All"

            self._user_table.setItem(row, 3, QTableWidgetItem(editor_rights))
            self._user_table.setItem(row, 4, QTableWidgetItem(viewer_rights))

    def _on_user_search_changed(self, text: str):
        """Handle user search text change."""
        self._refresh_user_table()

    def _on_open_existing_database(self):
        """Open an existing database file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Existing Database",
            "",
            "SQLite Database (*.db)"
        )

        if file_path:
            self._connect_to_database(file_path)

    def _on_create_new_database(self):
        """Create a new database file."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Create New Database",
            "issue_register.db",
            "SQLite Database (*.db)"
        )

        if file_path:
            self._connect_to_database(file_path)

    def _connect_to_database(self, file_path: str):
        """Connect to the specified database file."""
        try:
            # Change database path
            DatabaseConnection.set_database_path(file_path)

            # Run migrations if new
            from src.database.migrations import run_migrations
            run_migrations()

            # Save path to config file for next launch
            set_saved_database_path(file_path)

            self._db_path_edit.setText(file_path)
            self._db_status_label.setText("Connected")
            self._db_status_label.setStyleSheet("color: #059669;")

            QMessageBox.information(
                self,
                "Database Changed",
                f"Successfully connected to database:\n{file_path}\n\n"
                "Note: Restart the application for all changes to take effect."
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

    def _on_change_master_password(self):
        """Open dialog to change master password."""
        dialog = ChangeMasterPasswordDialog(parent=self)
        dialog.exec()

    def _on_change_password(self):
        """Open dialog for user to change their own password."""
        dialog = ChangePasswordDialog(forced=False, parent=self)
        dialog.exec()

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
            try:
                if self._auth.delete_user(user_id):
                    self._refresh_user_table()
                    QMessageBox.information(
                        self,
                        "User Deleted",
                        f"User '{username}' has been deleted successfully."
                    )
                else:
                    QMessageBox.critical(
                        self,
                        "Delete Failed",
                        "Cannot delete the last administrator account."
                    )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"An error occurred while deleting the user:\n{str(e)}"
                )

    def _on_export_backup(self):
        """Export database and attachments backup."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Backup",
            "issue_register_backup.zip",
            "ZIP Archive (*.zip)"
        )

        if not file_path:
            return

        success, error = self._export.backup_database(file_path)

        if success:
            QMessageBox.information(
                self,
                "Backup Complete",
                f"Database and attachments backup saved to:\n{file_path}"
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
        """Import database and attachments backup."""
        reply = QMessageBox.warning(
            self,
            "Confirm Import",
            "Importing a backup will OVERWRITE all current data and attachments.\n\n"
            "This action cannot be undone. Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Backup",
            "",
            "ZIP Archive (*.zip)"
        )

        if not file_path:
            return

        success, error = self._export.restore_database(file_path)

        if success:
            QMessageBox.information(
                self,
                "Import Complete",
                "Database and attachments restored successfully.\n"
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
        self.setMinimumSize(450, 350)

        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        form = QFormLayout()
        form.setSpacing(12)

        self._username_edit = QLineEdit()
        form.addRow("Username:", self._username_edit)

        # Password section - different for new vs edit
        if self._is_new:
            self._password_edit = QLineEdit()
            self._password_edit.setEchoMode(QLineEdit.EchoMode.Password)
            self._password_edit.setPlaceholderText("Enter password")
            form.addRow("Password:", self._password_edit)

            # Force password change checkbox (default checked for new users)
            self._force_pw_checkbox = QCheckBox("Require password change on first login")
            self._force_pw_checkbox.setChecked(True)
            self._force_pw_checkbox.setToolTip(
                "When checked, user must change their password after first login"
            )
            form.addRow("", self._force_pw_checkbox)
        else:
            # For existing users, show Reset Password button
            self._password_edit = None  # No direct password edit
            self._force_pw_checkbox = None

            pw_layout = QHBoxLayout()
            self._reset_pw_btn = QPushButton("Reset Password")
            self._reset_pw_btn.clicked.connect(self._on_reset_password)
            pw_layout.addWidget(self._reset_pw_btn)
            pw_layout.addStretch()
            form.addRow("Password:", pw_layout)

        self._role_combo = QComboBox()
        for role in UserRole.values():
            self._role_combo.addItem(role)
        self._role_combo.currentTextChanged.connect(self._on_role_changed)
        form.addRow("Role:", self._role_combo)

        layout.addLayout(form)

        # Load departments once
        self._all_departments = []
        try:
            self._all_departments = queries.get_distinct_values("department")
        except Exception:
            pass

        # Departments (for Restricted/Viewer)
        self._dept_group = QGroupBox("Department Access")
        dept_layout = QVBoxLayout(self._dept_group)

        dept_note = QLabel("Select departments this user can access:")
        dept_note.setProperty("muted", True)
        dept_layout.addWidget(dept_note)

        self._dept_combo = MultiSelectComboBox("All Departments")
        self._dept_combo.set_items(self._all_departments)
        dept_layout.addWidget(self._dept_combo)

        layout.addWidget(self._dept_group)

        # Editor department restrictions (two dropdowns)
        self._editor_dept_group = QGroupBox("Editor Department Restrictions")
        editor_dept_layout = QVBoxLayout(self._editor_dept_group)

        # View departments
        view_label = QLabel("Departments this editor can VIEW:")
        view_label.setProperty("muted", True)
        editor_dept_layout.addWidget(view_label)

        self._view_dept_combo = MultiSelectComboBox("All Departments")
        self._view_dept_combo.set_items(self._all_departments)
        editor_dept_layout.addWidget(self._view_dept_combo)

        # Edit departments
        edit_label = QLabel("Departments this editor can EDIT:")
        edit_label.setProperty("muted", True)
        editor_dept_layout.addWidget(edit_label)

        self._edit_dept_combo = MultiSelectComboBox("All Departments")
        self._edit_dept_combo.set_items(self._all_departments)
        editor_dept_layout.addWidget(self._edit_dept_combo)

        edit_note = QLabel("Select 'All Departments' for unrestricted access.")
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

        # Pre-select departments for Restricted/Viewer
        if self._user.departments:
            self._dept_combo._selected = list(self._user.departments)
            self._dept_combo._update_display_label()
        else:
            # Empty means all departments - select all
            self._dept_combo._selected = list(self._all_departments)
            self._dept_combo._update_display_label()

        # Pre-select view/edit departments for Editor
        if self._user.view_departments:
            self._view_dept_combo._selected = list(self._user.view_departments)
            self._view_dept_combo._update_display_label()
        else:
            # Empty means all departments - select all
            self._view_dept_combo._selected = list(self._all_departments)
            self._view_dept_combo._update_display_label()

        if self._user.edit_departments:
            self._edit_dept_combo._selected = list(self._user.edit_departments)
            self._edit_dept_combo._update_display_label()
        else:
            # Empty means all departments - select all
            self._edit_dept_combo._selected = list(self._all_departments)
            self._edit_dept_combo._update_display_label()

    def _on_role_changed(self, role: str):
        """Show/hide departments based on role."""
        # Restricted/Viewer: single department list
        show_restricted_depts = role in [UserRole.RESTRICTED.value, UserRole.VIEWER.value]
        self._dept_group.setVisible(show_restricted_depts)

        # Editor: two department lists (view + edit)
        show_editor_depts = role == UserRole.EDITOR.value
        self._editor_dept_group.setVisible(show_editor_depts)

        # Resize dialog to fit content
        self.adjustSize()

    def _on_reset_password(self):
        """Reset password for existing user (admin function)."""
        dialog = ResetPasswordDialog(self._user.username, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_password = dialog.get_password()
            force_change = dialog.get_force_change()

            if self._auth.reset_user_password(self._user.id, new_password, force_change):
                msg = f"Password for '{self._user.username}' has been reset."
                if force_change:
                    msg += "\nUser will be required to change password on next login."
                QMessageBox.information(self, "Password Reset", msg)
            else:
                QMessageBox.critical(self, "Error", "Failed to reset password.")

    def _on_save(self):
        """Save user."""
        username = self._username_edit.text().strip()
        role = self._role_combo.currentText()

        if not username:
            QMessageBox.warning(self, "Validation", "Username is required.")
            return

        # Get password only for new users
        password = None
        force_password_change = True
        if self._is_new:
            password = self._password_edit.text()
            force_password_change = self._force_pw_checkbox.isChecked()

            if not password:
                QMessageBox.warning(self, "Validation", "Password is required for new users.")
                return

        # Get selected departments based on role
        # If all departments are selected, save empty list (means unrestricted)
        departments = []
        view_departments = []
        edit_departments = []

        if role in [UserRole.RESTRICTED.value, UserRole.VIEWER.value]:
            selected = self._dept_combo.get_selected()
            # Empty list means unrestricted (all selected)
            if len(selected) == len(self._all_departments):
                departments = []
            else:
                departments = selected
        elif role == UserRole.EDITOR.value:
            view_selected = self._view_dept_combo.get_selected()
            edit_selected = self._edit_dept_combo.get_selected()
            # Empty list means unrestricted (all selected)
            if len(view_selected) == len(self._all_departments):
                view_departments = []
            else:
                view_departments = view_selected
            if len(edit_selected) == len(self._all_departments):
                edit_departments = []
            else:
                edit_departments = edit_selected

        try:
            if self._is_new:
                user = self._auth.create_user(
                    username, password, role, departments,
                    view_departments=view_departments,
                    edit_departments=edit_departments,
                    force_password_change=force_password_change
                )
                if not user:
                    QMessageBox.critical(
                        self,
                        "Error",
                        f"Username '{username}' already exists."
                    )
                    return

                QMessageBox.information(
                    self,
                    "User Created",
                    f"User '{username}' has been created successfully."
                )
            else:
                user = self._auth.update_user(
                    self._user.id,
                    username=username,
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

                QMessageBox.information(
                    self,
                    "User Updated",
                    f"User '{username}' has been updated successfully."
                )

            self.accept()

        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"An error occurred while saving the user:\n{str(e)}"
            )


class ChangePasswordDialog(QDialog):
    """Dialog for users to change their own password."""

    def __init__(self, forced: bool = False, parent=None):
        """
        Initialize change password dialog.

        Args:
            forced: If True, user cannot cancel (must change password)
            parent: Parent widget
        """
        super().__init__(parent)

        self._auth = get_auth_service()
        self._forced = forced

        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        """Set up dialog UI."""
        self.setWindowTitle("Change Password")
        self.setMinimumWidth(400)

        if self._forced:
            # Prevent closing without changing password
            self.setWindowFlag(Qt.WindowType.WindowCloseButtonHint, False)

        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        # Instructions
        if self._forced:
            instructions = QLabel(
                "You must change your password before continuing.\n"
                "Please enter your current password and choose a new one."
            )
            instructions.setStyleSheet("color: #B91C1C;")
        else:
            instructions = QLabel(
                "Enter your current password and choose a new password."
            )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)

        form = QFormLayout()
        form.setSpacing(12)

        self._current_pw_edit = QLineEdit()
        self._current_pw_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._current_pw_edit.setPlaceholderText("Enter current password")
        form.addRow("Current Password:", self._current_pw_edit)

        self._new_pw_edit = QLineEdit()
        self._new_pw_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._new_pw_edit.setPlaceholderText("Enter new password")
        form.addRow("New Password:", self._new_pw_edit)

        self._confirm_pw_edit = QLineEdit()
        self._confirm_pw_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._confirm_pw_edit.setPlaceholderText("Confirm new password")
        form.addRow("Confirm Password:", self._confirm_pw_edit)

        layout.addLayout(form)

        # Password requirements note
        note = QLabel("Password must be at least 6 characters.")
        note.setProperty("muted", True)
        layout.addWidget(note)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        if not self._forced:
            cancel_btn = QPushButton("Cancel")
            cancel_btn.clicked.connect(self.reject)
            btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Change Password")
        save_btn.setProperty("primary", True)
        save_btn.clicked.connect(self._on_save)
        btn_layout.addWidget(save_btn)

        layout.addLayout(btn_layout)

    def _connect_signals(self):
        """Connect signals."""
        self._confirm_pw_edit.returnPressed.connect(self._on_save)

    def _on_save(self):
        """Save new password."""
        current_pw = self._current_pw_edit.text()
        new_pw = self._new_pw_edit.text()
        confirm_pw = self._confirm_pw_edit.text()

        # Validation
        if not current_pw:
            QMessageBox.warning(self, "Validation", "Please enter your current password.")
            self._current_pw_edit.setFocus()
            return

        if not new_pw:
            QMessageBox.warning(self, "Validation", "Please enter a new password.")
            self._new_pw_edit.setFocus()
            return

        if len(new_pw) < 6:
            QMessageBox.warning(self, "Validation", "New password must be at least 6 characters.")
            self._new_pw_edit.setFocus()
            return

        if new_pw != confirm_pw:
            QMessageBox.warning(self, "Validation", "New passwords do not match.")
            self._confirm_pw_edit.setFocus()
            return

        if current_pw == new_pw:
            QMessageBox.warning(self, "Validation", "New password must be different from current password.")
            self._new_pw_edit.setFocus()
            return

        # Try to change password
        success, error = self._auth.change_own_password(current_pw, new_pw)

        if success:
            QMessageBox.information(
                self,
                "Password Changed",
                "Your password has been changed successfully."
            )
            self.accept()
        else:
            QMessageBox.critical(self, "Error", error)
            self._current_pw_edit.clear()
            self._current_pw_edit.setFocus()

    def reject(self):
        """Override reject to prevent closing when forced."""
        if self._forced:
            QMessageBox.warning(
                self,
                "Password Change Required",
                "You must change your password before continuing."
            )
            return
        super().reject()


class ResetPasswordDialog(QDialog):
    """Dialog for admin to reset a user's password."""

    def __init__(self, username: str, parent=None):
        super().__init__(parent)

        self._username = username
        self._password = ""
        self._force_change = True

        self._setup_ui()

    def _setup_ui(self):
        """Set up dialog UI."""
        self.setWindowTitle("Reset Password")
        self.setMinimumWidth(400)

        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        # Instructions
        instructions = QLabel(f"Set a new password for user '{self._username}':")
        layout.addWidget(instructions)

        form = QFormLayout()
        form.setSpacing(12)

        self._new_pw_edit = QLineEdit()
        self._new_pw_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._new_pw_edit.setPlaceholderText("Enter new password")
        form.addRow("New Password:", self._new_pw_edit)

        self._confirm_pw_edit = QLineEdit()
        self._confirm_pw_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._confirm_pw_edit.setPlaceholderText("Confirm new password")
        form.addRow("Confirm Password:", self._confirm_pw_edit)

        layout.addLayout(form)

        # Force password change checkbox
        self._force_change_checkbox = QCheckBox("Require user to change password on next login")
        self._force_change_checkbox.setChecked(True)
        layout.addWidget(self._force_change_checkbox)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        reset_btn = QPushButton("Reset Password")
        reset_btn.setProperty("primary", True)
        reset_btn.clicked.connect(self._on_reset)
        btn_layout.addWidget(reset_btn)

        layout.addLayout(btn_layout)

    def _on_reset(self):
        """Handle reset button click."""
        new_pw = self._new_pw_edit.text()
        confirm_pw = self._confirm_pw_edit.text()

        if not new_pw:
            QMessageBox.warning(self, "Validation", "Please enter a new password.")
            self._new_pw_edit.setFocus()
            return

        if len(new_pw) < 6:
            QMessageBox.warning(self, "Validation", "Password must be at least 6 characters.")
            self._new_pw_edit.setFocus()
            return

        if new_pw != confirm_pw:
            QMessageBox.warning(self, "Validation", "Passwords do not match.")
            self._confirm_pw_edit.setFocus()
            return

        self._password = new_pw
        self._force_change = self._force_change_checkbox.isChecked()
        self.accept()

    def get_password(self) -> str:
        """Get the new password."""
        return self._password

    def get_force_change(self) -> bool:
        """Get whether to force password change."""
        return self._force_change


class ChangeMasterPasswordDialog(QDialog):
    """Dialog for changing the master recovery password."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self._auth = get_auth_service()

        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        """Set up dialog UI."""
        self.setWindowTitle("Change Master Password")
        self.setMinimumWidth(400)

        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        # Instructions
        instructions = QLabel(
            "The master password is used for account recovery when users\n"
            "forget their passwords. Keep this password secure."
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)

        form = QFormLayout()
        form.setSpacing(12)

        self._current_pw_edit = QLineEdit()
        self._current_pw_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._current_pw_edit.setPlaceholderText("Enter current master password")
        form.addRow("Current Password:", self._current_pw_edit)

        self._new_pw_edit = QLineEdit()
        self._new_pw_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._new_pw_edit.setPlaceholderText("Enter new master password")
        form.addRow("New Password:", self._new_pw_edit)

        self._confirm_pw_edit = QLineEdit()
        self._confirm_pw_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._confirm_pw_edit.setPlaceholderText("Confirm new master password")
        form.addRow("Confirm Password:", self._confirm_pw_edit)

        layout.addLayout(form)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Change Password")
        save_btn.setProperty("primary", True)
        save_btn.clicked.connect(self._on_save)
        btn_layout.addWidget(save_btn)

        layout.addLayout(btn_layout)

    def _connect_signals(self):
        """Connect signals."""
        self._confirm_pw_edit.returnPressed.connect(self._on_save)

    def _on_save(self):
        """Save new master password."""
        current_pw = self._current_pw_edit.text()
        new_pw = self._new_pw_edit.text()
        confirm_pw = self._confirm_pw_edit.text()

        # Validation
        if not current_pw:
            QMessageBox.warning(self, "Validation", "Please enter the current master password.")
            self._current_pw_edit.setFocus()
            return

        if not new_pw:
            QMessageBox.warning(self, "Validation", "Please enter a new master password.")
            self._new_pw_edit.setFocus()
            return

        if len(new_pw) < 8:
            QMessageBox.warning(self, "Validation", "New password must be at least 8 characters.")
            self._new_pw_edit.setFocus()
            return

        if new_pw != confirm_pw:
            QMessageBox.warning(self, "Validation", "New passwords do not match.")
            self._confirm_pw_edit.setFocus()
            return

        # Verify current master password
        if not self._auth.verify_master_password(current_pw):
            QMessageBox.critical(self, "Error", "Current master password is incorrect.")
            self._current_pw_edit.clear()
            self._current_pw_edit.setFocus()
            return

        # Update master password
        try:
            from src.database.migrations import set_master_password
            set_master_password(new_pw)

            QMessageBox.information(
                self,
                "Password Changed",
                "Master password has been changed successfully."
            )
            self.accept()

        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to change master password:\n{str(e)}"
            )
