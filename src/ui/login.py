"""Login dialog for user authentication and database selection."""

from pathlib import Path

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QPushButton, QLabel, QMessageBox, QFrame,
    QFileDialog, QCheckBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from src.services.auth import get_auth_service
from src.services.config import get_saved_database_path, set_saved_database_path, is_database_path_valid
from src.database.models import User


class LoginDialog(QDialog):
    """
    Login dialog for user authentication.

    Returns QDialog.Accepted if login successful, QDialog.Rejected otherwise.

    Emits:
        database_change_requested: When user wants to change database
    """

    database_change_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self._auth = get_auth_service()
        self._logged_in_user = None

        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        """Set up the dialog UI."""
        self.setWindowTitle("Issue Register - Login")
        self.setMinimumWidth(400)
        self.setModal(True)
        self.adjustSize()

        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(40, 40, 40, 40)

        # Title
        title = QLabel("Issue Register")
        title.setProperty("heading", True)
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # Subtitle
        subtitle = QLabel("Please sign in to continue")
        subtitle.setProperty("muted", True)
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        layout.addSpacing(20)

        # Form
        form_layout = QFormLayout()
        form_layout.setSpacing(12)

        self._username_edit = QLineEdit()
        self._username_edit.setPlaceholderText("Username")
        form_layout.addRow("Username:", self._username_edit)

        self._password_edit = QLineEdit()
        self._password_edit.setPlaceholderText("Password")
        self._password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        form_layout.addRow("Password:", self._password_edit)

        layout.addLayout(form_layout)

        # Error label
        self._error_label = QLabel()
        self._error_label.setStyleSheet("color: #DC2626;")
        self._error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._error_label.hide()
        layout.addWidget(self._error_label)

        # Buttons
        button_layout = QHBoxLayout()

        self._forgot_btn = QPushButton("Forgot Password")
        self._forgot_btn.setFlat(True)
        self._forgot_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        button_layout.addWidget(self._forgot_btn)

        button_layout.addStretch()

        self._login_btn = QPushButton("Login")
        self._login_btn.setProperty("primary", True)
        self._login_btn.setDefault(True)
        button_layout.addWidget(self._login_btn)

        layout.addLayout(button_layout)

        layout.addStretch()

        # Change Database link at bottom
        change_db_layout = QHBoxLayout()
        change_db_layout.addStretch()
        self._change_db_btn = QPushButton("Change Database")
        self._change_db_btn.setFlat(True)
        self._change_db_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        change_db_layout.addWidget(self._change_db_btn)
        change_db_layout.addStretch()
        layout.addLayout(change_db_layout)

    def _connect_signals(self):
        """Connect button signals."""
        self._login_btn.clicked.connect(self._on_login)
        self._forgot_btn.clicked.connect(self._on_forgot_password)
        self._change_db_btn.clicked.connect(self._on_change_database)
        self._password_edit.returnPressed.connect(self._on_login)
        self._username_edit.returnPressed.connect(self._focus_password)

    def _focus_password(self):
        """Focus password field when Enter pressed in username."""
        self._password_edit.setFocus()

    def _on_login(self):
        """Handle login button click."""
        username = self._username_edit.text().strip()
        password = self._password_edit.text()

        if not username:
            self._show_error("Please enter your username")
            self._username_edit.setFocus()
            return

        if not password:
            self._show_error("Please enter your password")
            self._password_edit.setFocus()
            return

        user = self._auth.authenticate(username, password)
        if user:
            self._auth.login(user)
            self._logged_in_user = user

            # Check if user must change password
            if user.force_password_change:
                from src.ui.settings import ChangePasswordDialog
                dialog = ChangePasswordDialog(forced=True, parent=self)
                if dialog.exec() == QDialog.DialogCode.Accepted:
                    # Password was changed, refresh user data
                    from src.database import queries
                    self._logged_in_user = queries.get_user(user.id)
                    self._auth._current_user = self._logged_in_user
                    self.accept()
                else:
                    # User didn't change password (shouldn't happen with forced=True)
                    # But just in case, don't allow login
                    self._auth.logout()
                    self._logged_in_user = None
                    self._show_error("You must change your password to continue")
                    return
            else:
                self.accept()
        else:
            self._show_error("Invalid username or password")
            self._password_edit.clear()
            self._password_edit.setFocus()

    def _on_forgot_password(self):
        """Handle forgot password link click."""
        dialog = MasterPasswordDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Grant temporary admin access
            self._auth.login_as_admin()
            self._logged_in_user = self._auth.current_user

            QMessageBox.information(
                self,
                "Password Recovery",
                "You have been granted temporary administrator access.\n\n"
                "Please go to Settings to reset your password or create a new account."
            )
            self.accept()

    def _on_change_database(self):
        """Handle change database link click."""
        self.database_change_requested.emit()
        self.reject()

    def _show_error(self, message: str):
        """Show error message."""
        self._error_label.setText(message)
        self._error_label.show()

    def get_user(self) -> User:
        """Get the logged in user."""
        return self._logged_in_user


class MasterPasswordDialog(QDialog):
    """Dialog for master password entry during password recovery."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self._auth = get_auth_service()

        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        """Set up the dialog UI."""
        self.setWindowTitle("Password Recovery")
        self.setFixedSize(350, 200)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        # Instructions
        instructions = QLabel(
            "Enter the master password to gain temporary\n"
            "administrator access for password recovery."
        )
        instructions.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(instructions)

        # Password field
        form_layout = QFormLayout()
        self._password_edit = QLineEdit()
        self._password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._password_edit.setPlaceholderText("Master Password")
        form_layout.addRow("Master Password:", self._password_edit)
        layout.addLayout(form_layout)

        # Error label
        self._error_label = QLabel()
        self._error_label.setStyleSheet("color: #DC2626;")
        self._error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._error_label.hide()
        layout.addWidget(self._error_label)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        verify_btn = QPushButton("Verify")
        verify_btn.setProperty("primary", True)
        verify_btn.clicked.connect(self._on_verify)
        verify_btn.setDefault(True)
        button_layout.addWidget(verify_btn)

        layout.addLayout(button_layout)

    def _connect_signals(self):
        """Connect signals."""
        self._password_edit.returnPressed.connect(self._on_verify)

    def _on_verify(self):
        """Handle verify button click."""
        password = self._password_edit.text()

        if not password:
            self._error_label.setText("Please enter the master password")
            self._error_label.show()
            return

        if self._auth.verify_master_password(password):
            self.accept()
        else:
            self._error_label.setText("Invalid master password")
            self._error_label.show()
            self._password_edit.clear()
            self._password_edit.setFocus()


class DatabaseSelectionDialog(QDialog):
    """
    Dialog for selecting database location.

    Shows on first launch or when user requests database change.
    """

    def __init__(self, current_path: str = None, error_message: str = None, parent=None):
        """
        Initialize database selection dialog.

        Args:
            current_path: Current database path to show (if any)
            error_message: Error message to display (e.g., "Database not found")
            parent: Parent widget
        """
        super().__init__(parent)

        self._selected_path = current_path or ""
        self._error_message = error_message
        self._is_new_database = False

        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        """Set up the dialog UI."""
        self.setWindowTitle("Issue Register - Select Database")
        self.setMinimumWidth(500)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(40, 40, 40, 40)

        # Title
        title = QLabel("Issue Register")
        title.setProperty("heading", True)
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # Subtitle
        subtitle = QLabel("Select Database Location")
        subtitle.setProperty("muted", True)
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        layout.addSpacing(10)

        # Instructions
        instructions = QLabel(
            "Connect to an existing database or create a new one."
        )
        instructions.setAlignment(Qt.AlignmentFlag.AlignCenter)
        instructions.setWordWrap(True)
        layout.addWidget(instructions)

        layout.addSpacing(10)

        # Error message (if any)
        self._error_label = QLabel()
        self._error_label.setStyleSheet("color: #DC2626;")
        self._error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if self._error_message:
            self._error_label.setText(self._error_message)
        else:
            self._error_label.hide()
        layout.addWidget(self._error_label)

        # Database selection buttons
        browse_btn_layout = QHBoxLayout()
        browse_btn_layout.addStretch()

        self._open_existing_btn = QPushButton("Open Existing Database")
        browse_btn_layout.addWidget(self._open_existing_btn)

        self._create_new_btn = QPushButton("Create New Database")
        browse_btn_layout.addWidget(self._create_new_btn)

        browse_btn_layout.addStretch()
        layout.addLayout(browse_btn_layout)

        layout.addSpacing(10)

        # Path display
        path_layout = QHBoxLayout()
        path_label = QLabel("Location:")
        path_layout.addWidget(path_label)
        self._path_edit = QLineEdit()
        self._path_edit.setPlaceholderText("No database selected...")
        self._path_edit.setReadOnly(True)
        if self._selected_path:
            self._path_edit.setText(self._selected_path)
        path_layout.addWidget(self._path_edit, 1)
        layout.addLayout(path_layout)

        # Status indicator
        self._status_label = QLabel()
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._update_status()
        layout.addWidget(self._status_label)

        layout.addStretch()

        # Connect button
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self._connect_btn = QPushButton("Connect")
        self._connect_btn.setProperty("primary", True)
        self._connect_btn.setDefault(True)
        self._connect_btn.setEnabled(bool(self._selected_path))
        button_layout.addWidget(self._connect_btn)

        layout.addLayout(button_layout)

    def _connect_signals(self):
        """Connect signals."""
        self._open_existing_btn.clicked.connect(self._on_open_existing)
        self._create_new_btn.clicked.connect(self._on_create_new)
        self._connect_btn.clicked.connect(self._on_connect)

    def _on_open_existing(self):
        """Handle open existing database button click."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Existing Database",
            "",
            "SQLite Database (*.db)"
        )

        if file_path:
            self._selected_path = file_path
            self._is_new_database = False
            self._path_edit.setText(file_path)
            self._connect_btn.setEnabled(True)
            self._error_label.hide()
            self._update_status()

    def _on_create_new(self):
        """Handle create new database button click."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Create New Database",
            "issue_register.db",
            "SQLite Database (*.db)"
        )

        if file_path:
            self._selected_path = file_path
            self._is_new_database = True
            self._path_edit.setText(file_path)
            self._connect_btn.setEnabled(True)
            self._error_label.hide()
            self._update_status()

    def _update_status(self):
        """Update the status label based on selected path."""
        if not self._selected_path:
            self._status_label.setText("")
            return

        path = Path(self._selected_path)
        if path.exists():
            self._status_label.setText("Ready to connect to existing database")
            self._status_label.setStyleSheet("color: #059669;")
        else:
            self._status_label.setText("New database will be created")
            self._status_label.setStyleSheet("color: #2563EB;")

    def _on_connect(self):
        """Handle connect button click."""
        if not self._selected_path:
            self._error_label.setText("Please select a database location")
            self._error_label.show()
            return

        # Validate the path
        path = Path(self._selected_path)
        parent = path.parent

        if not parent.exists():
            self._error_label.setText("The selected folder does not exist")
            self._error_label.show()
            return

        # Save the path and accept
        set_saved_database_path(self._selected_path)
        self.accept()

    def get_selected_path(self) -> str:
        """Get the selected database path."""
        return self._selected_path
