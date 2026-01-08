"""Login dialog for user authentication."""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QPushButton, QLabel, QMessageBox, QFrame
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from src.services.auth import get_auth_service
from src.database.models import User


class LoginDialog(QDialog):
    """
    Login dialog for user authentication.

    Returns QDialog.Accepted if login successful, QDialog.Rejected otherwise.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self._auth = get_auth_service()
        self._logged_in_user = None

        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        """Set up the dialog UI."""
        self.setWindowTitle("Issue Register - Login")
        self.setFixedSize(400, 300)
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

    def _connect_signals(self):
        """Connect button signals."""
        self._login_btn.clicked.connect(self._on_login)
        self._forgot_btn.clicked.connect(self._on_forgot_password)
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
