"""Filter panel widget for issue filtering."""

from datetime import date
from typing import Optional

from PySide6.QtWidgets import (
    QGroupBox, QVBoxLayout, QHBoxLayout, QFormLayout,
    QComboBox, QDateEdit, QPushButton, QLabel, QCheckBox,
    QWidget, QListWidget, QListWidgetItem, QFrame, QSplitter,
    QScrollArea
)
from PySide6.QtCore import Signal, Qt, QDate
from PySide6.QtGui import QCursor

from src.database.models import Status, RiskLevel
from src.database import queries


class MultiSelectComboBox(QWidget):
    """
    A combo box that allows multiple selections via checkboxes.

    Features:
    - Single click opens a floating popup
    - Click anywhere on a row to toggle selection
    - "All" option to select/deselect all items
    - "Done" button to close popup
    - Click outside popup to close
    - Displays "N selected" when multiple items are chosen
    """

    selection_changed = Signal(list)

    def __init__(self, placeholder: str = "All", parent=None):
        super().__init__(parent)

        self._placeholder = placeholder
        self._items = []
        self._selected = []
        self._popup = None
        self._updating_all = False  # Prevent recursion when toggling "All"

        self._setup_ui()

    def _setup_ui(self):
        """Set up the UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Trigger button (looks like a combo box)
        self._trigger = QFrame()
        self._trigger.setObjectName("multiSelectTrigger")
        self._trigger.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._trigger.setFixedHeight(32)
        self._trigger.mousePressEvent = self._on_trigger_clicked

        trigger_layout = QHBoxLayout(self._trigger)
        trigger_layout.setContentsMargins(10, 0, 10, 0)
        trigger_layout.setSpacing(8)

        self._display_label = QLabel(self._placeholder)
        self._display_label.setObjectName("multiSelectLabel")
        trigger_layout.addWidget(self._display_label)

        trigger_layout.addStretch()

        arrow_label = QLabel("▼")
        arrow_label.setObjectName("multiSelectArrow")
        trigger_layout.addWidget(arrow_label)

        layout.addWidget(self._trigger)

    def _on_trigger_clicked(self, event):
        """Show popup when trigger is clicked."""
        if self._popup and self._popup.isVisible():
            self._close_popup()
        else:
            self._show_popup()

    def _show_popup(self):
        """Show the selection popup."""
        if not self._items:
            return

        # Create popup window
        self._popup = QFrame(self, Qt.WindowType.Popup)
        self._popup.setObjectName("multiSelectPopup")
        self._popup.setMinimumWidth(self._trigger.width())
        self._popup.setMaximumWidth(max(self._trigger.width(), 250))

        popup_layout = QVBoxLayout(self._popup)
        popup_layout.setContentsMargins(0, 0, 0, 0)
        popup_layout.setSpacing(0)

        # "All" option at top
        all_row = self._create_checkbox_row("All", is_all_option=True)
        popup_layout.addWidget(all_row)

        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setObjectName("popupSeparator")
        popup_layout.addWidget(separator)

        # Scrollable list of items
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setMaximumHeight(200)

        list_container = QWidget()
        list_layout = QVBoxLayout(list_container)
        list_layout.setContentsMargins(0, 0, 0, 0)
        list_layout.setSpacing(0)

        self._checkboxes = {}
        for item in self._items:
            row = self._create_checkbox_row(item)
            list_layout.addWidget(row)
            # Restore previously selected state (block signals to prevent updates during init)
            checkbox = self._checkboxes[item]
            checkbox.blockSignals(True)
            checkbox.setChecked(item in self._selected)
            checkbox.blockSignals(False)

        list_layout.addStretch()
        scroll.setWidget(list_container)
        popup_layout.addWidget(scroll)

        # Separator before Done button
        separator2 = QFrame()
        separator2.setFrameShape(QFrame.Shape.HLine)
        separator2.setObjectName("popupSeparator")
        popup_layout.addWidget(separator2)

        # Done button
        done_btn = QPushButton("Done")
        done_btn.setObjectName("popupDoneButton")
        done_btn.clicked.connect(self._close_popup)
        popup_layout.addWidget(done_btn)

        # Update "All" checkbox state
        self._update_all_checkbox_state()

        # Position popup below trigger
        global_pos = self._trigger.mapToGlobal(self._trigger.rect().bottomLeft())
        self._popup.move(global_pos)
        self._popup.show()

    def _create_checkbox_row(self, text: str, is_all_option: bool = False) -> QFrame:
        """Create a clickable row with checkbox."""
        row = QFrame()
        row.setObjectName("checkboxRow")
        row.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(10, 6, 10, 6)
        row_layout.setSpacing(8)

        checkbox = QCheckBox()
        checkbox.setObjectName("rowCheckbox")
        if is_all_option:
            checkbox.setObjectName("allCheckbox")
            checkbox.stateChanged.connect(self._on_all_toggled)
            self._all_checkbox = checkbox
        else:
            checkbox.stateChanged.connect(lambda state, t=text: self._on_item_toggled(t, state))
            self._checkboxes[text] = checkbox

        row_layout.addWidget(checkbox)

        label = QLabel(text)
        label.setObjectName("rowLabel")
        row_layout.addWidget(label)
        row_layout.addStretch()

        # Make entire row clickable
        def on_row_clicked(event, cb=checkbox):
            cb.setChecked(not cb.isChecked())

        row.mousePressEvent = on_row_clicked

        return row

    def _on_all_toggled(self, state):
        """Handle 'All' checkbox toggle."""
        if self._updating_all:
            return

        self._updating_all = True
        is_checked = state == Qt.CheckState.Checked.value

        for checkbox in self._checkboxes.values():
            checkbox.setChecked(is_checked)

        self._updating_all = False
        self._update_selected()

    def _on_item_toggled(self, item: str, state):
        """Handle individual item toggle."""
        self._update_selected()
        self._update_all_checkbox_state()

    def _update_all_checkbox_state(self):
        """Update 'All' checkbox based on individual selections."""
        if self._updating_all or not hasattr(self, '_all_checkbox'):
            return

        self._updating_all = True
        all_checked = all(cb.isChecked() for cb in self._checkboxes.values())
        none_checked = not any(cb.isChecked() for cb in self._checkboxes.values())

        if all_checked:
            self._all_checkbox.setCheckState(Qt.CheckState.Checked)
        elif none_checked:
            self._all_checkbox.setCheckState(Qt.CheckState.Unchecked)
        else:
            self._all_checkbox.setCheckState(Qt.CheckState.PartiallyChecked)

        self._updating_all = False

    def _update_selected(self):
        """Update selected items list and display text."""
        self._selected = [
            item for item, checkbox in self._checkboxes.items()
            if checkbox.isChecked()
        ]
        self._update_display_label()
        self.selection_changed.emit(self._selected)

    def _close_popup(self):
        """Close the popup."""
        if self._popup:
            self._popup.close()
            self._popup = None

    def set_items(self, items: list[str]):
        """Set the available items, preserving existing valid selections."""
        self._items = items
        # Preserve selections that still exist in the new items list
        self._selected = [s for s in self._selected if s in items]
        self._checkboxes = {}
        self._update_display_label()

    def _update_display_label(self):
        """Update the display label based on current selection."""
        if not self._selected:
            self._display_label.setText(self._placeholder)
        elif len(self._selected) == 1:
            self._display_label.setText(self._selected[0])
        elif self._items and len(self._selected) == len(self._items):
            self._display_label.setText(self._placeholder)
        else:
            self._display_label.setText(f"{len(self._selected)} selected")

    def get_selected(self) -> list[str]:
        """Get list of selected items."""
        return self._selected.copy()

    def clear_selection(self):
        """Clear all selections."""
        self._selected = []
        self._display_label.setText(self._placeholder)
        # If popup is open, update checkboxes
        if self._popup and self._popup.isVisible():
            for checkbox in self._checkboxes.values():
                checkbox.setChecked(False)
        self.selection_changed.emit(self._selected)

    def hide_list(self):
        """Hide the dropdown list (for compatibility)."""
        self._close_popup()


class FilterPanel(QGroupBox):
    """
    Filter panel for issue list filtering.

    Emits filter_changed signal when any filter value changes.
    Emits delete_requested signal when delete button is clicked.
    """

    filter_changed = Signal()
    delete_requested = Signal()

    def __init__(self, parent=None):
        super().__init__("Filters", parent)

        self._delete_btn: QPushButton = None

        self._setup_ui()
        self._connect_signals()
        self._load_filter_options()

    def _setup_ui(self):
        """Set up the filter panel UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Status filter (multi-select)
        status_layout = QFormLayout()
        self._status_combo = MultiSelectComboBox("All Statuses")
        self._status_combo.set_items(Status.values())
        status_layout.addRow("Status:", self._status_combo)
        layout.addLayout(status_layout)

        # Risk Level filter (multi-select)
        risk_layout = QFormLayout()
        self._risk_combo = MultiSelectComboBox("All Risk Levels")
        self._risk_combo.set_items(RiskLevel.values())
        risk_layout.addRow("Risk Level:", self._risk_combo)
        layout.addLayout(risk_layout)

        # Department filter (multi-select)
        dept_layout = QFormLayout()
        self._dept_combo = MultiSelectComboBox("All Departments")
        dept_layout.addRow("Department:", self._dept_combo)
        layout.addLayout(dept_layout)

        # Owner filter (multi-select)
        owner_layout = QFormLayout()
        self._owner_combo = MultiSelectComboBox("All Owners")
        owner_layout.addRow("Owner:", self._owner_combo)
        layout.addLayout(owner_layout)

        # Topic filter (multi-select)
        topic_layout = QFormLayout()
        self._topic_combo = MultiSelectComboBox("All Topics")
        topic_layout.addRow("Topic:", self._topic_combo)
        layout.addLayout(topic_layout)

        # Identified By filter (multi-select) - NEW
        identified_layout = QFormLayout()
        self._identified_combo = MultiSelectComboBox("All")
        identified_layout.addRow("Identified By:", self._identified_combo)
        layout.addLayout(identified_layout)

        # Due date range - vertical layout with From/To on separate lines
        date_label = QLabel("Due Date Range:")
        layout.addWidget(date_label)

        # From row
        date_from_layout = QHBoxLayout()
        date_from_layout.setSpacing(6)
        self._date_from_enabled = QCheckBox()
        date_from_layout.addWidget(self._date_from_enabled)
        date_from_layout.addWidget(QLabel("From:"))
        self._date_from = QDateEdit()
        self._date_from.setCalendarPopup(True)
        self._date_from.setDisplayFormat("dd/MM/yyyy")
        self._date_from.setDate(QDate(2000, 1, 1))
        self._date_from.setFixedWidth(140)
        date_from_layout.addWidget(self._date_from)
        date_from_layout.addStretch()
        layout.addLayout(date_from_layout)

        # To row
        date_to_layout = QHBoxLayout()
        date_to_layout.setSpacing(6)
        self._date_to_enabled = QCheckBox()
        date_to_layout.addWidget(self._date_to_enabled)
        date_to_layout.addWidget(QLabel("To:"))
        self._date_to = QDateEdit()
        self._date_to.setCalendarPopup(True)
        self._date_to.setDisplayFormat("dd/MM/yyyy")
        self._date_to.setDate(QDate.currentDate().addMonths(1))
        self._date_to.setFixedWidth(140)
        date_to_layout.addWidget(self._date_to)
        date_to_layout.addStretch()
        layout.addLayout(date_to_layout)

        # Identification Date range - vertical layout
        id_date_label = QLabel("Identification Date:")
        layout.addWidget(id_date_label)

        # From row
        id_from_layout = QHBoxLayout()
        id_from_layout.setSpacing(6)
        self._id_date_from_enabled = QCheckBox()
        id_from_layout.addWidget(self._id_date_from_enabled)
        id_from_layout.addWidget(QLabel("From:"))
        self._id_date_from = QDateEdit()
        self._id_date_from.setCalendarPopup(True)
        self._id_date_from.setDisplayFormat("dd/MM/yyyy")
        self._id_date_from.setDate(QDate(2000, 1, 1))
        self._id_date_from.setFixedWidth(140)
        id_from_layout.addWidget(self._id_date_from)
        id_from_layout.addStretch()
        layout.addLayout(id_from_layout)

        # To row
        id_to_layout = QHBoxLayout()
        id_to_layout.setSpacing(6)
        self._id_date_to_enabled = QCheckBox()
        id_to_layout.addWidget(self._id_date_to_enabled)
        id_to_layout.addWidget(QLabel("To:"))
        self._id_date_to = QDateEdit()
        self._id_date_to.setCalendarPopup(True)
        self._id_date_to.setDisplayFormat("dd/MM/yyyy")
        self._id_date_to.setDate(QDate.currentDate())
        self._id_date_to.setFixedWidth(140)
        id_to_layout.addWidget(self._id_date_to)
        id_to_layout.addStretch()
        layout.addLayout(id_to_layout)

        # Clear filters button
        clear_btn = QPushButton("Clear Filters")
        clear_btn.clicked.connect(self.clear_filters)
        layout.addWidget(clear_btn)

        # Delete button (admin only - hidden by default)
        self._delete_btn = QPushButton("Delete Filtered Issues")
        self._delete_btn.setProperty("danger", True)
        self._delete_btn.clicked.connect(self.delete_requested.emit)
        self._delete_btn.setVisible(False)  # Hidden until set_delete_visible is called
        layout.addWidget(self._delete_btn)

        layout.addStretch()

    def _connect_signals(self):
        """Connect filter change signals."""
        self._status_combo.selection_changed.connect(self._on_filter_changed)
        self._risk_combo.selection_changed.connect(self._on_filter_changed)
        self._dept_combo.selection_changed.connect(self._on_filter_changed)
        self._owner_combo.selection_changed.connect(self._on_filter_changed)
        self._topic_combo.selection_changed.connect(self._on_filter_changed)
        self._identified_combo.selection_changed.connect(self._on_filter_changed)
        self._date_from.dateChanged.connect(self._on_filter_changed)
        self._date_to.dateChanged.connect(self._on_filter_changed)
        self._date_from_enabled.stateChanged.connect(self._on_filter_changed)
        self._date_to_enabled.stateChanged.connect(self._on_filter_changed)
        self._id_date_from.dateChanged.connect(self._on_filter_changed)
        self._id_date_to.dateChanged.connect(self._on_filter_changed)
        self._id_date_from_enabled.stateChanged.connect(self._on_filter_changed)
        self._id_date_to_enabled.stateChanged.connect(self._on_filter_changed)

    def _on_filter_changed(self, *args):
        """Emit filter changed signal."""
        self.filter_changed.emit()

    def _load_filter_options(self):
        """Load filter options from database."""
        self.refresh_options()

    def refresh_options(self):
        """Refresh dropdown options from database."""
        try:
            # Department
            self._dept_combo.set_items(queries.get_distinct_values("department"))

            # Owner
            self._owner_combo.set_items(queries.get_distinct_values("owner"))

            # Topic
            self._topic_combo.set_items(queries.get_distinct_values("topic"))

            # Identified By
            self._identified_combo.set_items(queries.get_distinct_values("identified_by"))

        except Exception:
            # Database may not be initialized yet
            pass

    def get_filters(self) -> dict:
        """
        Get current filter values.

        Returns:
            Dictionary with filter parameters for queries.list_issues()
        """
        filters = {}

        # Status (multi-select)
        selected_status = self._status_combo.get_selected()
        if selected_status:
            filters["status"] = selected_status

        # Risk level (multi-select)
        selected_risk = self._risk_combo.get_selected()
        if selected_risk:
            filters["risk_level"] = selected_risk

        # Department (multi-select)
        selected_dept = self._dept_combo.get_selected()
        if selected_dept:
            filters["department"] = selected_dept

        # Owner (multi-select)
        selected_owner = self._owner_combo.get_selected()
        if selected_owner:
            filters["owner"] = selected_owner

        # Topic (multi-select)
        selected_topic = self._topic_combo.get_selected()
        if selected_topic:
            filters["topic"] = selected_topic

        # Identified By (multi-select)
        selected_identified = self._identified_combo.get_selected()
        if selected_identified:
            filters["identified_by"] = selected_identified

        # Due Date range
        if self._date_from_enabled.isChecked():
            filters["due_date_from"] = self._date_from.date().toPython()

        if self._date_to_enabled.isChecked():
            filters["due_date_to"] = self._date_to.date().toPython()

        # Identification Date range
        if self._id_date_from_enabled.isChecked():
            filters["identification_date_from"] = self._id_date_from.date().toPython()

        if self._id_date_to_enabled.isChecked():
            filters["identification_date_to"] = self._id_date_to.date().toPython()

        return filters

    def clear_filters(self):
        """Reset all filters to default values."""
        self._status_combo.clear_selection()
        self._risk_combo.clear_selection()
        self._dept_combo.clear_selection()
        self._owner_combo.clear_selection()
        self._topic_combo.clear_selection()
        self._identified_combo.clear_selection()
        self._date_from_enabled.setChecked(False)
        self._date_to_enabled.setChecked(False)
        self._date_from.setDate(QDate(2000, 1, 1))
        self._date_to.setDate(QDate.currentDate().addMonths(1))
        self._id_date_from_enabled.setChecked(False)
        self._id_date_to_enabled.setChecked(False)
        self._id_date_from.setDate(QDate(2000, 1, 1))
        self._id_date_to.setDate(QDate.currentDate())

        self.filter_changed.emit()

    def has_active_filters(self) -> bool:
        """Check if any filters are active."""
        return bool(self.get_filters())

    def set_delete_visible(self, visible: bool) -> None:
        """Show or hide the delete button (for admin users only)."""
        if self._delete_btn:
            self._delete_btn.setVisible(visible)


class CollapsibleFilterPanel(QWidget):
    """
    Filter panel that collapses to a vertical blue strip.

    When collapsed, shows a blue strip with "FILTERS" text vertically.
    Click anywhere on the strip to expand.
    """

    filter_changed = Signal()
    delete_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self._is_collapsed = False
        self._setup_ui()

    def _setup_ui(self):
        """Set up the UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Collapsed strip (vertical blue bar with "FILTERS" text)
        self._collapsed_strip = QFrame()
        self._collapsed_strip.setFixedWidth(28)
        self._collapsed_strip.setStyleSheet("""
            QFrame {
                background-color: #2D3E50;
                border-radius: 4px;
            }
        """)
        self._collapsed_strip.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._collapsed_strip.mousePressEvent = self._on_strip_clicked

        # Vertical label inside strip
        strip_layout = QVBoxLayout(self._collapsed_strip)
        strip_layout.setContentsMargins(4, 12, 4, 12)
        self._strip_label = QLabel("F\nI\nL\nT\nE\nR\nS")
        self._strip_label.setStyleSheet("color: white; font-weight: bold; font-size: 11px;")
        self._strip_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        strip_layout.addWidget(self._strip_label, alignment=Qt.AlignmentFlag.AlignCenter)
        strip_layout.addStretch()

        # Actual filter panel
        self._filter_panel = FilterPanel()
        self._filter_panel.filter_changed.connect(self.filter_changed.emit)
        self._filter_panel.delete_requested.connect(self.delete_requested.emit)

        layout.addWidget(self._collapsed_strip)
        layout.addWidget(self._filter_panel)

        # Initially show expanded
        self._collapsed_strip.hide()

    def _on_strip_clicked(self, event):
        """Handle click on collapsed strip."""
        self.expand()

    def collapse(self):
        """Collapse the filter panel to a strip."""
        self._is_collapsed = True
        self._filter_panel.hide()
        self._collapsed_strip.show()

    def expand(self):
        """Expand the filter panel."""
        self._is_collapsed = False
        self._collapsed_strip.hide()
        self._filter_panel.show()

    def toggle(self):
        """Toggle collapsed state."""
        if self._is_collapsed:
            self.expand()
        else:
            self.collapse()

    def is_collapsed(self) -> bool:
        """Check if panel is collapsed."""
        return self._is_collapsed

    # Delegate methods to internal filter panel
    def get_filters(self) -> dict:
        """Get current filter values."""
        return self._filter_panel.get_filters()

    def refresh_options(self):
        """Refresh filter options."""
        self._filter_panel.refresh_options()

    def clear_filters(self):
        """Clear all filters."""
        self._filter_panel.clear_filters()

    def has_active_filters(self) -> bool:
        """Check if any filters are active."""
        return self._filter_panel.has_active_filters()

    def set_delete_visible(self, visible: bool) -> None:
        """Show or hide the delete button (for admin users only)."""
        self._filter_panel.set_delete_visible(visible)
