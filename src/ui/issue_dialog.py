"""Issue detail dialog for viewing and editing issues."""

from datetime import date
from typing import Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGridLayout,
    QLineEdit, QTextEdit, QComboBox, QDateEdit, QPushButton,
    QLabel, QGroupBox, QScrollArea, QWidget, QMessageBox,
    QFileDialog, QListWidget, QListWidgetItem
)
from PySide6.QtCore import Qt, QDate

from src.database.models import Issue, User, Status, RiskLevel
from src.database import queries
from src.services.auth import get_auth_service
from src.services.permissions import get_permission_service
from src.services.issue_service import get_issue_service


class IssueDialog(QDialog):
    """
    Dialog for viewing and editing issue details.

    Modes:
    - Create: New issue creation
    - Edit: Existing issue editing (permission-aware)
    - View: Read-only viewing
    """

    def __init__(
        self,
        issue: Optional[Issue] = None,
        user: Optional[User] = None,
        parent=None
    ):
        super().__init__(parent)

        self._issue = issue
        self._user = user or get_auth_service().current_user
        self._permissions = get_permission_service()
        self._issue_service = get_issue_service()
        self._is_new = issue is None

        self._setup_ui()
        self._populate_dropdowns()

        if issue:
            self._load_issue()

        self._apply_permissions()

    def _setup_ui(self):
        """Set up the dialog UI."""
        title = "New Issue" if self._is_new else f"Issue #{self._issue.id}"
        self.setWindowTitle(title)
        self.setMinimumSize(800, 700)

        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        # Scroll area for content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(16)

        # Basic Information
        basic_group = QGroupBox("Basic Information")
        basic_layout = QFormLayout(basic_group)
        basic_layout.setSpacing(12)

        self._title_edit = QLineEdit()
        self._title_edit.setPlaceholderText("Enter issue title...")
        basic_layout.addRow("Title *:", self._title_edit)

        self._status_combo = QComboBox()
        for status in Status.values():
            self._status_combo.addItem(status)
        basic_layout.addRow("Status:", self._status_combo)

        self._summary_edit = QTextEdit()
        self._summary_edit.setMaximumHeight(80)
        self._summary_edit.setPlaceholderText("Brief summary of the issue...")
        basic_layout.addRow("Summary:", self._summary_edit)

        content_layout.addWidget(basic_group)

        # Classification
        class_group = QGroupBox("Classification")
        class_layout = QGridLayout(class_group)
        class_layout.setSpacing(12)

        class_layout.addWidget(QLabel("Topic:"), 0, 0)
        self._topic_combo = QComboBox()
        self._topic_combo.setEditable(True)
        self._topic_combo.lineEdit().setPlaceholderText("Select or type new...")
        class_layout.addWidget(self._topic_combo, 0, 1)

        class_layout.addWidget(QLabel("Department:"), 0, 2)
        self._dept_combo = QComboBox()
        self._dept_combo.setEditable(True)
        self._dept_combo.lineEdit().setPlaceholderText("Select or type new...")
        class_layout.addWidget(self._dept_combo, 0, 3)

        class_layout.addWidget(QLabel("Identified By:"), 1, 0)
        self._identified_combo = QComboBox()
        self._identified_combo.setEditable(True)
        self._identified_combo.lineEdit().setPlaceholderText("Select or type new...")
        class_layout.addWidget(self._identified_combo, 1, 1)

        class_layout.addWidget(QLabel("Owner:"), 1, 2)
        self._owner_combo = QComboBox()
        self._owner_combo.setEditable(True)
        self._owner_combo.lineEdit().setPlaceholderText("Select or type new...")
        class_layout.addWidget(self._owner_combo, 1, 3)

        content_layout.addWidget(class_group)

        # Details
        details_group = QGroupBox("Details")
        details_layout = QFormLayout(details_group)
        details_layout.setSpacing(12)

        self._description_edit = QTextEdit()
        self._description_edit.setMinimumHeight(100)
        self._description_edit.setPlaceholderText("Detailed description of the issue...")
        details_layout.addRow("Description:", self._description_edit)

        self._remediation_edit = QTextEdit()
        self._remediation_edit.setMinimumHeight(80)
        self._remediation_edit.setPlaceholderText("Planned or completed corrective actions...")
        details_layout.addRow("Remediation:", self._remediation_edit)

        content_layout.addWidget(details_group)

        # Risk Assessment
        risk_group = QGroupBox("Risk Assessment")
        risk_layout = QFormLayout(risk_group)
        risk_layout.setSpacing(12)

        self._risk_level_combo = QComboBox()
        for risk in RiskLevel.values():
            self._risk_level_combo.addItem(risk)
        risk_layout.addRow("Risk Level:", self._risk_level_combo)

        self._risk_desc_edit = QTextEdit()
        self._risk_desc_edit.setMaximumHeight(80)
        self._risk_desc_edit.setPlaceholderText("Assessment of potential impact...")
        risk_layout.addRow("Risk Description:", self._risk_desc_edit)

        content_layout.addWidget(risk_group)

        # Dates
        dates_group = QGroupBox("Dates")
        dates_layout = QGridLayout(dates_group)
        dates_layout.setSpacing(12)

        dates_layout.addWidget(QLabel("Identification Date:"), 0, 0)
        self._id_date = QDateEdit()
        self._id_date.setCalendarPopup(True)
        self._id_date.setDate(QDate.currentDate())
        dates_layout.addWidget(self._id_date, 0, 1)

        dates_layout.addWidget(QLabel("Due Date:"), 0, 2)
        self._due_date = QDateEdit()
        self._due_date.setCalendarPopup(True)
        self._due_date.setSpecialValueText("Not set")
        dates_layout.addWidget(self._due_date, 0, 3)

        dates_layout.addWidget(QLabel("Follow-up Date:"), 1, 0)
        self._followup_date = QDateEdit()
        self._followup_date.setCalendarPopup(True)
        self._followup_date.setSpecialValueText("Not set")
        dates_layout.addWidget(self._followup_date, 1, 1)

        dates_layout.addWidget(QLabel("Closing Date:"), 1, 2)
        self._closing_date = QDateEdit()
        self._closing_date.setCalendarPopup(True)
        self._closing_date.setSpecialValueText("Not set")
        self._closing_date.setEnabled(False)  # Auto-set
        dates_layout.addWidget(self._closing_date, 1, 3)

        content_layout.addWidget(dates_group)

        # Updates
        updates_group = QGroupBox("Progress Updates")
        updates_layout = QVBoxLayout(updates_group)

        self._updates_edit = QTextEdit()
        self._updates_edit.setMinimumHeight(100)
        self._updates_edit.setPlaceholderText("Chronological progress notes...")
        updates_layout.addWidget(self._updates_edit)

        content_layout.addWidget(updates_group)

        # Supporting Documents
        docs_group = QGroupBox("Supporting Documents")
        docs_layout = QVBoxLayout(docs_group)

        self._docs_list = QListWidget()
        self._docs_list.setMaximumHeight(100)
        docs_layout.addWidget(self._docs_list)

        docs_btn_layout = QHBoxLayout()
        self._add_doc_btn = QPushButton("Add File")
        self._add_doc_btn.clicked.connect(self._on_add_document)
        docs_btn_layout.addWidget(self._add_doc_btn)

        self._remove_doc_btn = QPushButton("Remove")
        self._remove_doc_btn.clicked.connect(self._on_remove_document)
        docs_btn_layout.addWidget(self._remove_doc_btn)

        docs_btn_layout.addStretch()
        docs_layout.addLayout(docs_btn_layout)

        content_layout.addWidget(docs_group)

        content_layout.addStretch()

        scroll.setWidget(content)
        layout.addWidget(scroll, 1)

        # Buttons
        button_layout = QHBoxLayout()

        if not self._is_new:
            self._delete_btn = QPushButton("Delete")
            self._delete_btn.setProperty("danger", True)
            self._delete_btn.clicked.connect(self._on_delete)
            button_layout.addWidget(self._delete_btn)

        button_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        self._save_btn = QPushButton("Save")
        self._save_btn.setProperty("primary", True)
        self._save_btn.clicked.connect(self._on_save)
        button_layout.addWidget(self._save_btn)

        layout.addLayout(button_layout)

    def _populate_dropdowns(self):
        """Populate combo boxes with existing values."""
        try:
            # Topic
            self._topic_combo.clear()
            self._topic_combo.addItem("")
            for topic in queries.get_distinct_values("topic"):
                self._topic_combo.addItem(topic)

            # Department
            self._dept_combo.clear()
            self._dept_combo.addItem("")
            for dept in queries.get_distinct_values("department"):
                self._dept_combo.addItem(dept)

            # Identified By
            self._identified_combo.clear()
            self._identified_combo.addItem("")
            for person in queries.get_distinct_values("identified_by"):
                self._identified_combo.addItem(person)

            # Owner
            self._owner_combo.clear()
            self._owner_combo.addItem("")
            for owner in queries.get_distinct_values("owner"):
                self._owner_combo.addItem(owner)

        except Exception:
            pass

    def _load_issue(self):
        """Load issue data into form."""
        if not self._issue:
            return

        self._title_edit.setText(self._issue.title or "")

        idx = self._status_combo.findText(self._issue.status)
        if idx >= 0:
            self._status_combo.setCurrentIndex(idx)

        self._summary_edit.setPlainText(self._issue.summary_description or "")
        self._topic_combo.setCurrentText(self._issue.topic or "")
        self._dept_combo.setCurrentText(self._issue.department or "")
        self._identified_combo.setCurrentText(self._issue.identified_by or "")
        self._owner_combo.setCurrentText(self._issue.owner or "")
        self._description_edit.setPlainText(self._issue.description or "")
        self._remediation_edit.setPlainText(self._issue.remediation_action or "")

        idx = self._risk_level_combo.findText(self._issue.risk_level)
        if idx >= 0:
            self._risk_level_combo.setCurrentIndex(idx)

        self._risk_desc_edit.setPlainText(self._issue.risk_description or "")

        if self._issue.identification_date:
            self._id_date.setDate(QDate(
                self._issue.identification_date.year,
                self._issue.identification_date.month,
                self._issue.identification_date.day
            ))

        if self._issue.due_date:
            self._due_date.setDate(QDate(
                self._issue.due_date.year,
                self._issue.due_date.month,
                self._issue.due_date.day
            ))

        if self._issue.follow_up_date:
            self._followup_date.setDate(QDate(
                self._issue.follow_up_date.year,
                self._issue.follow_up_date.month,
                self._issue.follow_up_date.day
            ))

        if self._issue.closing_date:
            self._closing_date.setDate(QDate(
                self._issue.closing_date.year,
                self._issue.closing_date.month,
                self._issue.closing_date.day
            ))

        self._updates_edit.setPlainText(self._issue.updates or "")

        # Load documents
        self._docs_list.clear()
        for doc in self._issue.supporting_docs:
            self._docs_list.addItem(doc)

    def _apply_permissions(self):
        """Apply field permissions based on user role."""
        if not self._user:
            return

        if self._is_new:
            # New issue - check create permission
            if not self._permissions.can_create_issue(self._user):
                self._save_btn.setEnabled(False)
                return

            # Set default status
            default_status = self._permissions.get_default_status_for_role(self._user)
            idx = self._status_combo.findText(default_status)
            if idx >= 0:
                self._status_combo.setCurrentIndex(idx)
            return

        # Existing issue - check edit permission
        can_edit = self._permissions.can_edit_issue(self._user, self._issue)
        editable_fields = self._permissions.get_editable_fields(self._user, self._issue)

        if not can_edit:
            # Read-only mode
            self._set_all_readonly(True)
            self._save_btn.setEnabled(False)
            if hasattr(self, "_delete_btn"):
                self._delete_btn.setEnabled(False)
            return

        # Field-level permissions
        all_fields = [
            ("title", self._title_edit),
            ("summary_description", self._summary_edit),
            ("topic", self._topic_combo),
            ("department", self._dept_combo),
            ("identified_by", self._identified_combo),
            ("owner", self._owner_combo),
            ("description", self._description_edit),
            ("remediation_action", self._remediation_edit),
            ("risk_description", self._risk_desc_edit),
            ("risk_level", self._risk_level_combo),
            ("identification_date", self._id_date),
            ("due_date", self._due_date),
            ("follow_up_date", self._followup_date),
            ("updates", self._updates_edit),
            ("supporting_docs", self._docs_list),
        ]

        # Text widgets that support setReadOnly (keeps scrolling working)
        text_widgets = {
            self._title_edit, self._summary_edit, self._description_edit,
            self._remediation_edit, self._risk_desc_edit, self._updates_edit
        }

        for field_name, widget in all_fields:
            enabled = field_name in editable_fields
            if widget in text_widgets:
                # Use setReadOnly for text fields to keep scrolling functional
                widget.setReadOnly(not enabled)
            else:
                widget.setEnabled(enabled)

        # Status has special handling
        self._status_combo.setEnabled("status" in editable_fields)

        # Delete permission
        if hasattr(self, "_delete_btn"):
            self._delete_btn.setEnabled(
                self._permissions.can_delete_issue(self._user)
            )

    def _set_all_readonly(self, readonly: bool):
        """Set all fields to readonly."""
        # Text widgets use setReadOnly to keep scrolling functional
        text_widgets = [
            self._title_edit, self._summary_edit, self._description_edit,
            self._remediation_edit, self._risk_desc_edit, self._updates_edit
        ]
        for widget in text_widgets:
            widget.setReadOnly(readonly)

        # Other widgets use setEnabled
        other_widgets = [
            self._topic_combo, self._dept_combo, self._identified_combo,
            self._owner_combo, self._risk_level_combo, self._id_date,
            self._due_date, self._followup_date, self._status_combo
        ]
        for widget in other_widgets:
            widget.setEnabled(not readonly)

        self._add_doc_btn.setEnabled(not readonly)
        self._remove_doc_btn.setEnabled(not readonly)

    def _on_add_document(self):
        """Add supporting document."""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Supporting Documents",
            "",
            "All Files (*.*)"
        )

        for file_path in files:
            if file_path:
                self._docs_list.addItem(file_path)

    def _on_remove_document(self):
        """Remove selected document."""
        current = self._docs_list.currentRow()
        if current >= 0:
            self._docs_list.takeItem(current)

    def _on_save(self):
        """Save the issue."""
        # Validate
        title = self._title_edit.text().strip()
        if not title:
            QMessageBox.warning(self, "Validation Error", "Title is required.")
            self._title_edit.setFocus()
            return

        # Build issue from form
        issue = self._build_issue_from_form()

        if self._is_new:
            # Create new issue
            created, error = self._issue_service.create_issue(self._user, issue)
            if error:
                QMessageBox.critical(self, "Error", error)
                return
            QMessageBox.information(
                self,
                "Success",
                f"Issue #{created.id} created successfully."
            )
        else:
            # Update existing issue
            updates = self._get_updates_dict()
            updated, error = self._issue_service.update_issue(
                self._user, self._issue.id, updates
            )
            if error:
                QMessageBox.critical(self, "Error", error)
                return

        self.accept()

    def _build_issue_from_form(self) -> Issue:
        """Build Issue object from form values."""
        # Get supporting docs
        docs = []
        for i in range(self._docs_list.count()):
            docs.append(self._docs_list.item(i).text())

        return Issue(
            id=self._issue.id if self._issue else None,
            title=self._title_edit.text().strip(),
            status=self._status_combo.currentText(),
            summary_description=self._summary_edit.toPlainText().strip() or None,
            topic=self._topic_combo.currentText().strip() or None,
            department=self._dept_combo.currentText().strip() or None,
            identified_by=self._identified_combo.currentText().strip() or None,
            owner=self._owner_combo.currentText().strip() or None,
            description=self._description_edit.toPlainText().strip() or None,
            remediation_action=self._remediation_edit.toPlainText().strip() or None,
            risk_description=self._risk_desc_edit.toPlainText().strip() or None,
            risk_level=self._risk_level_combo.currentText(),
            identification_date=self._id_date.date().toPython(),
            due_date=self._due_date.date().toPython() if self._due_date.date().isValid() else None,
            follow_up_date=self._followup_date.date().toPython() if self._followup_date.date().isValid() else None,
            updates=self._updates_edit.toPlainText().strip() or None,
            closing_date=None,  # Auto-set by service
            supporting_docs=docs,
        )

    def _get_updates_dict(self) -> dict:
        """Get dictionary of updated values."""
        docs = []
        for i in range(self._docs_list.count()):
            docs.append(self._docs_list.item(i).text())

        return {
            "title": self._title_edit.text().strip(),
            "status": self._status_combo.currentText(),
            "summary_description": self._summary_edit.toPlainText().strip() or None,
            "topic": self._topic_combo.currentText().strip() or None,
            "department": self._dept_combo.currentText().strip() or None,
            "identified_by": self._identified_combo.currentText().strip() or None,
            "owner": self._owner_combo.currentText().strip() or None,
            "description": self._description_edit.toPlainText().strip() or None,
            "remediation_action": self._remediation_edit.toPlainText().strip() or None,
            "risk_description": self._risk_desc_edit.toPlainText().strip() or None,
            "risk_level": self._risk_level_combo.currentText(),
            "identification_date": self._id_date.date().toPython(),
            "due_date": self._due_date.date().toPython() if self._due_date.date().isValid() else None,
            "follow_up_date": self._followup_date.date().toPython() if self._followup_date.date().isValid() else None,
            "updates": self._updates_edit.toPlainText().strip() or None,
            "supporting_docs": docs,
        }

    def _on_delete(self):
        """Delete the issue."""
        if not self._issue:
            return

        reply = QMessageBox.warning(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete issue #{self._issue.id}?\n\n"
            "This action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            success, error = self._issue_service.delete_issue(
                self._user, self._issue.id
            )

            if success:
                self.accept()
            else:
                QMessageBox.critical(self, "Error", error)
