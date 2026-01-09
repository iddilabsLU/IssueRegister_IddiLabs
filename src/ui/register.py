"""Issue Register view - main data management interface."""

from typing import Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableView,
    QPushButton, QLabel, QHeaderView, QAbstractItemView,
    QMessageBox, QFileDialog, QSplitter, QFrame
)
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex, QSortFilterProxyModel
from PySide6.QtGui import QColor

from src.database.models import Issue, User, Status, RiskLevel
from src.database import queries
from src.services.auth import get_auth_service
from src.services.permissions import get_permission_service
from src.services.export import get_export_service
from src.ui.widgets.filter_panel import CollapsibleFilterPanel


class IssueTableModel(QAbstractTableModel):
    """Table model for displaying issues."""

    COLUMNS = [
        ("id", "ID"),
        ("title", "Title"),
        ("status", "Status"),
        ("topic", "Topic"),
        ("identified_by", "Identified By"),
        ("owner", "Owner"),
        ("risk_level", "Risk Level"),
        ("due_date", "Due Date"),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._issues: list[Issue] = []
        self._user: Optional[User] = None

    def set_user(self, user: User):
        """Set current user for permission filtering."""
        self._user = user

    def set_issues(self, issues: list[Issue]):
        """Update the issues list."""
        self.beginResetModel()
        self._issues = issues
        self.endResetModel()

    def get_issue(self, row: int) -> Optional[Issue]:
        """Get issue at row."""
        if 0 <= row < len(self._issues):
            return self._issues[row]
        return None

    def rowCount(self, parent=QModelIndex()):
        return len(self._issues)

    def columnCount(self, parent=QModelIndex()):
        return len(self.COLUMNS)

    def data(self, index: QModelIndex, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None

        issue = self._issues[index.row()]
        col_key = self.COLUMNS[index.column()][0]

        if role == Qt.ItemDataRole.DisplayRole:
            value = getattr(issue, col_key, "")
            if col_key == "due_date" and value:
                return value.isoformat()
            return str(value) if value else ""

        elif role == Qt.ItemDataRole.BackgroundRole:
            # Highlight overdue issues
            if issue.is_overdue():
                return QColor("#FEE2E2")  # Light red

        elif role == Qt.ItemDataRole.ForegroundRole:
            if col_key == "risk_level":
                colors = {
                    RiskLevel.HIGH.value: QColor("#DC2626"),
                    RiskLevel.MEDIUM.value: QColor("#D97706"),
                    RiskLevel.LOW.value: QColor("#059669"),
                }
                return colors.get(issue.risk_level)

        elif role == Qt.ItemDataRole.TextAlignmentRole:
            if col_key in ["id", "risk_level"]:
                return Qt.AlignmentFlag.AlignCenter

        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self.COLUMNS[section][1]
        return None


class RegisterView(QWidget):
    """
    Issue Register view with table, filters, and actions.

    Features:
    - Sortable/filterable table view
    - Filter panel
    - Create, edit, delete, export actions
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
        """Set up the view UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # Splitter for filter panel and table
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Filter panel (left side) - collapsible
        self._filter_panel = CollapsibleFilterPanel()
        self._filter_panel.setMaximumWidth(280)
        self._filter_panel.setMinimumWidth(28)  # Allow collapse to strip width
        splitter.addWidget(self._filter_panel)

        # Main content (right side)
        content = QFrame()
        content.setProperty("card", True)
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(16, 16, 16, 16)
        content_layout.setSpacing(12)

        # Header with actions
        header_layout = QHBoxLayout()

        title = QLabel("Issue Register")
        title.setProperty("heading", True)
        header_layout.addWidget(title)

        header_layout.addStretch()

        # Action buttons
        self._new_btn = QPushButton("+ New Issue")
        self._new_btn.setProperty("primary", True)
        header_layout.addWidget(self._new_btn)

        self._export_btn = QPushButton("Export")
        header_layout.addWidget(self._export_btn)

        self._refresh_btn = QPushButton("Refresh")
        header_layout.addWidget(self._refresh_btn)

        content_layout.addLayout(header_layout)

        # Table view
        self._table = QTableView()
        self._table.setAlternatingRowColors(True)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setSortingEnabled(True)
        self._table.setShowGrid(False)
        self._table.verticalHeader().setVisible(False)

        # Model
        self._model = IssueTableModel()
        self._proxy_model = QSortFilterProxyModel()
        self._proxy_model.setSourceModel(self._model)
        self._table.setModel(self._proxy_model)

        # Column sizing
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)  # ID
        header.resizeSection(0, 60)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Title
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)  # Status
        header.resizeSection(2, 100)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)  # Topic
        header.resizeSection(3, 120)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)  # Identified By
        header.resizeSection(4, 120)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)  # Owner
        header.resizeSection(5, 120)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)  # Risk Level
        header.resizeSection(6, 90)
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.Fixed)  # Due Date
        header.resizeSection(7, 100)

        content_layout.addWidget(self._table, 1)

        # Footer with count
        footer_layout = QHBoxLayout()
        self._count_label = QLabel("0 issues")
        self._count_label.setProperty("muted", True)
        footer_layout.addWidget(self._count_label)
        footer_layout.addStretch()
        content_layout.addLayout(footer_layout)

        splitter.addWidget(content)

        # Set splitter sizes
        splitter.setSizes([250, 950])

        layout.addWidget(splitter)

    def _connect_signals(self):
        """Connect signals."""
        self._new_btn.clicked.connect(self._on_new_issue)
        self._export_btn.clicked.connect(self._on_export)
        self._refresh_btn.clicked.connect(self.refresh)
        self._filter_panel.filter_changed.connect(self._apply_filters)
        self._filter_panel.delete_requested.connect(self._on_bulk_delete)
        self._table.doubleClicked.connect(self._on_row_double_click)

    def set_user(self, user: User):
        """Set current user and update permissions."""
        self._user = user
        self._model.set_user(user)

        # Update button visibility based on permissions
        can_create = self._permissions.can_create_issue(user)
        self._new_btn.setVisible(can_create)

        # Show delete button only for administrators
        can_delete = self._permissions.can_delete_issue(user)
        self._filter_panel.set_delete_visible(can_delete)

        self.refresh()

    def refresh(self):
        """Refresh the issue list."""
        self._filter_panel.refresh_options()
        self._apply_filters()

    def _apply_filters(self):
        """Apply current filters and reload data."""
        if not self._user:
            return

        filters = self._filter_panel.get_filters()

        # Get filtered issues
        from src.services.issue_service import get_issue_service
        issue_service = get_issue_service()

        issues = issue_service.list_issues(
            self._user,
            **filters
        )

        self._model.set_issues(issues)
        self._count_label.setText(f"{len(issues)} issues")

    def _on_new_issue(self):
        """Open dialog to create new issue."""
        from src.ui.issue_dialog import IssueDialog

        dialog = IssueDialog(user=self._user, parent=self)
        if dialog.exec():
            self.refresh()

    def _on_row_double_click(self, index: QModelIndex):
        """Handle double-click on table row."""
        source_index = self._proxy_model.mapToSource(index)
        issue = self._model.get_issue(source_index.row())

        if issue:
            self._open_issue_dialog(issue)

    def _open_issue_dialog(self, issue: Issue):
        """Open dialog to view/edit issue."""
        from src.ui.issue_dialog import IssueDialog

        dialog = IssueDialog(issue=issue, user=self._user, parent=self)
        if dialog.exec():
            self.refresh()

    def _on_export(self):
        """Export issues to Excel."""
        if not self._user:
            return

        # Get filtered issues
        filters = self._filter_panel.get_filters()
        from src.services.issue_service import get_issue_service
        issue_service = get_issue_service()

        issues = issue_service.list_issues(self._user, **filters)

        if not issues:
            QMessageBox.information(
                self,
                "Export",
                "No issues to export."
            )
            return

        # Get save path
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Issues",
            "issues_export.xlsx",
            "Excel Files (*.xlsx)"
        )

        if not file_path:
            return

        # Export
        success, error = self._export.export_issues_to_excel(issues, file_path)

        if success:
            QMessageBox.information(
                self,
                "Export Complete",
                f"Successfully exported {len(issues)} issues to:\n{file_path}"
            )
        else:
            QMessageBox.critical(
                self,
                "Export Failed",
                f"Failed to export issues:\n{error}"
            )

    def _on_bulk_delete(self):
        """Handle bulk delete request."""
        if not self._user:
            return

        # Double-check permissions
        if not self._permissions.can_delete_issue(self._user):
            QMessageBox.critical(
                self,
                "Permission Denied",
                "Only Administrators can delete issues."
            )
            return

        # Get current filtered issues
        filters = self._filter_panel.get_filters()
        from src.services.issue_service import get_issue_service
        issue_service = get_issue_service()

        issues = issue_service.list_issues(self._user, **filters)

        if not issues:
            QMessageBox.information(
                self,
                "No Issues",
                "There are no issues to delete with the current filters."
            )
            return

        # Show confirmation dialog
        from src.ui.bulk_delete_dialog import BulkDeleteDialog

        dialog = BulkDeleteDialog(
            issues=issues,
            filters=filters,
            user=self._user,
            parent=self
        )

        if not dialog.exec():
            return  # User cancelled

        # Export if requested
        if dialog.should_export():
            export_path = dialog.get_export_path()
            if export_path:
                success, error = self._export.export_issues_to_excel(issues, export_path)
                if not success:
                    reply = QMessageBox.warning(
                        self,
                        "Export Failed",
                        f"Failed to export issues:\n{error}\n\n"
                        "Do you want to continue with deletion anyway?",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                        QMessageBox.StandardButton.No
                    )
                    if reply == QMessageBox.StandardButton.No:
                        return

        # Perform deletion
        deleted_count = 0
        failed_count = 0
        failed_issues = []

        for issue in issues:
            success, error = issue_service.delete_issue(self._user, issue.id)
            if success:
                deleted_count += 1
            else:
                failed_count += 1
                failed_issues.append(f"ID {issue.id}: {error}")

        # Log bulk delete action
        from src.services.audit import get_audit_service
        get_audit_service().log_bulk_delete(
            self._user,
            deleted_count,
            filters
        )

        # Show result
        if failed_count == 0:
            QMessageBox.information(
                self,
                "Deletion Complete",
                f"Successfully deleted {deleted_count} issue(s)."
            )
        else:
            error_details = "\n".join(failed_issues[:5])  # Show first 5 errors
            if len(failed_issues) > 5:
                error_details += f"\n... and {len(failed_issues) - 5} more"

            QMessageBox.warning(
                self,
                "Deletion Partially Complete",
                f"Deleted {deleted_count} issue(s).\n"
                f"Failed to delete {failed_count} issue(s):\n\n{error_details}"
            )

        # Refresh the view
        self.refresh()
