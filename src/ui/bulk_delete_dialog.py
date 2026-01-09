"""Bulk delete confirmation dialog with password verification."""

from typing import Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QCheckBox, QGroupBox,
    QFormLayout, QMessageBox, QFileDialog
)
from PySide6.QtCore import Qt

from src.database.models import User, Issue
from src.services.auth import AuthService


class BulkDeleteDialog(QDialog):
    """
    Confirmation dialog for bulk delete operations.

    Features:
    - Shows number of issues to be deleted
    - Displays active filter summary
    - Optional export before delete
    - Password verification required
    """

    def __init__(
        self,
        issues: list[Issue],
        filters: dict,
        user: User,
        parent=None
    ):
        super().__init__(parent)

        self._issues = issues
        self._filters = filters
        self._user = user
        self._export_before_delete = False
        self._export_path: Optional[str] = None

        self.setWindowTitle("Confirm Bulk Delete")
        self.setModal(True)
        self.setMinimumWidth(450)

        self._setup_ui()

    def _setup_ui(self):
        """Set up the dialog UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        # Warning icon and count
        warning_layout = QHBoxLayout()
        warning_icon = QLabel("\u26a0")  # Warning symbol
        warning_icon.setStyleSheet("font-size: 32px; color: #B91C1C;")
        warning_layout.addWidget(warning_icon)

        count_label = QLabel(f"<b>{len(self._issues)}</b> issue(s) will be deleted")
        count_label.setStyleSheet("font-size: 16px;")
        warning_layout.addWidget(count_label)
        warning_layout.addStretch()
        layout.addLayout(warning_layout)

        # Filter summary (if any filters are active)
        if self._filters:
            filter_group = QGroupBox("Active Filters")
            filter_layout = QVBoxLayout(filter_group)
            filter_layout.setSpacing(4)

            filter_text = self._build_filter_summary()
            filter_label = QLabel(filter_text)
            filter_label.setWordWrap(True)
            filter_label.setStyleSheet("color: #6B7280;")
            filter_layout.addWidget(filter_label)

            layout.addWidget(filter_group)
        else:
            no_filter_label = QLabel(
                "<b>Warning:</b> No filters applied. "
                "<span style='color: #B91C1C;'>ALL issues will be deleted!</span>"
            )
            no_filter_label.setWordWrap(True)
            layout.addWidget(no_filter_label)

        # Export option
        self._export_checkbox = QCheckBox("Export to Excel before deleting (recommended)")
        self._export_checkbox.setChecked(True)  # Default to checked for safety
        layout.addWidget(self._export_checkbox)

        # Warning message
        warning_text = QLabel(
            "<span style='color: #B91C1C;'>"
            "This action cannot be undone. "
            "Please verify you want to delete these issues."
            "</span>"
        )
        warning_text.setWordWrap(True)
        layout.addWidget(warning_text)

        # Password verification
        auth_group = QGroupBox("Authentication Required")
        auth_layout = QFormLayout(auth_group)

        self._password_input = QLineEdit()
        self._password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._password_input.setPlaceholderText("Enter your account password")
        self._password_input.returnPressed.connect(self._on_delete_clicked)
        auth_layout.addRow("Password:", self._password_input)

        layout.addWidget(auth_group)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        self._delete_btn = QPushButton(f"Delete {len(self._issues)} Issue(s)")
        self._delete_btn.setProperty("danger", True)
        self._delete_btn.clicked.connect(self._on_delete_clicked)
        button_layout.addWidget(self._delete_btn)

        layout.addLayout(button_layout)

        # Focus on password field
        self._password_input.setFocus()

    def _build_filter_summary(self) -> str:
        """Build human-readable filter summary."""
        lines = []

        filter_labels = {
            "status": "Status",
            "risk_level": "Risk Level",
            "department": "Department",
            "owner": "Owner",
            "topic": "Topic",
            "identified_by": "Identified By",
            "due_date_from": "Due Date From",
            "due_date_to": "Due Date To",
            "identification_date_from": "Identification Date From",
            "identification_date_to": "Identification Date To",
        }

        for key, label in filter_labels.items():
            if key in self._filters:
                value = self._filters[key]
                if isinstance(value, list):
                    value_str = ", ".join(value)
                else:
                    value_str = str(value)
                lines.append(f"\u2022 {label}: {value_str}")

        return "\n".join(lines) if lines else "No filters applied"

    def _on_delete_clicked(self):
        """Handle delete button click."""
        password = self._password_input.text().strip()

        if not password:
            QMessageBox.warning(
                self,
                "Password Required",
                "Please enter your password to confirm deletion."
            )
            self._password_input.setFocus()
            return

        # Verify password
        if not AuthService.verify_password(password, self._user.password_hash):
            QMessageBox.critical(
                self,
                "Authentication Failed",
                "Incorrect password. Please try again."
            )
            self._password_input.clear()
            self._password_input.setFocus()
            return

        # Handle export if requested
        if self._export_checkbox.isChecked():
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Export Issues Before Deletion",
                "issues_backup.xlsx",
                "Excel Files (*.xlsx)"
            )

            if not file_path:
                # User cancelled export - ask if they want to continue
                reply = QMessageBox.question(
                    self,
                    "Skip Export?",
                    "You cancelled the export. Do you want to continue with deletion without exporting?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.No:
                    return
            else:
                self._export_path = file_path
                self._export_before_delete = True

        self.accept()

    def should_export(self) -> bool:
        """Check if export was requested and path provided."""
        return self._export_before_delete

    def get_export_path(self) -> Optional[str]:
        """Get the export file path."""
        return self._export_path

    def get_issues_to_delete(self) -> list[Issue]:
        """Get the list of issues to delete."""
        return self._issues
