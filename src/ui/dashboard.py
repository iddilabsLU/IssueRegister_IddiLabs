"""Dashboard view with analytics and visualizations."""

from typing import Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QScrollArea, QLabel, QFrame, QSplitter
)
from PySide6.QtCore import Qt

from src.database.models import User, Status, RiskLevel
from src.services.auth import get_auth_service
from src.services.issue_service import get_issue_service
from src.ui.widgets.kpi_card import KPICard
from src.ui.widgets.charts import PieChartWidget, StackedBarChartWidget, ProgressBarWidget, CHART_COLORS
from src.ui.widgets.filter_panel import CollapsibleFilterPanel


class DashboardView(QWidget):
    """
    Dashboard view with KPIs, charts, and analytics.

    Features:
    - KPI cards (Total, Active, High Priority, Overdue, Resolution Rate)
    - Status and Risk distribution pie charts
    - Progress bars for resolution metrics
    - Department and Topic stacked bar charts
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self._auth = get_auth_service()
        self._issue_service = get_issue_service()
        self._user: Optional[User] = None

        self._setup_ui()

    def _setup_ui(self):
        """Set up the dashboard UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # Splitter for filter panel and dashboard content
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Filter panel (left side) - collapsible
        self._filter_panel = CollapsibleFilterPanel()
        self._filter_panel.setMaximumWidth(280)
        self._filter_panel.setMinimumWidth(28)  # Allow collapse to strip width
        # Connect to _apply_filters, NOT refresh (to avoid clearing selections)
        self._filter_panel.filter_changed.connect(self._apply_filters)
        splitter.addWidget(self._filter_panel)

        # Main scroll area (right side)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        content = QWidget()
        main_layout = QVBoxLayout(content)
        main_layout.setSpacing(24)
        main_layout.setContentsMargins(24, 24, 24, 24)

        # Header
        header = QLabel("Dashboard")
        header.setProperty("heading", True)
        main_layout.addWidget(header)

        # KPI Cards Row
        kpi_layout = QHBoxLayout()
        kpi_layout.setSpacing(16)

        self._kpi_total = KPICard("Total Issues", 0)
        kpi_layout.addWidget(self._kpi_total)

        self._kpi_active = KPICard("Active Issues", 0)
        kpi_layout.addWidget(self._kpi_active)

        self._kpi_high_priority = KPICard("High Priority Open", 0, priority="high")
        kpi_layout.addWidget(self._kpi_high_priority)

        self._kpi_overdue = KPICard("Overdue", 0, priority="high")
        kpi_layout.addWidget(self._kpi_overdue)

        self._kpi_resolution = KPICard("Resolution Rate", 0, suffix="%")
        kpi_layout.addWidget(self._kpi_resolution)

        main_layout.addLayout(kpi_layout)

        # Charts Row 1: Pie Charts
        charts_row1 = QHBoxLayout()
        charts_row1.setSpacing(16)

        # Status Distribution
        status_frame = QFrame()
        status_frame.setProperty("card", True)
        status_layout = QVBoxLayout(status_frame)
        self._status_chart = PieChartWidget("Status Distribution", donut=True)
        status_layout.addWidget(self._status_chart)
        charts_row1.addWidget(status_frame)

        # Risk Distribution
        risk_frame = QFrame()
        risk_frame.setProperty("card", True)
        risk_layout = QVBoxLayout(risk_frame)
        self._risk_chart = PieChartWidget("Risk Level Distribution", donut=True)
        risk_layout.addWidget(self._risk_chart)
        charts_row1.addWidget(risk_frame)

        main_layout.addLayout(charts_row1)

        # Progress Bars Section
        progress_frame = QFrame()
        progress_frame.setProperty("card", True)
        progress_layout = QVBoxLayout(progress_frame)
        progress_layout.setSpacing(16)

        progress_title = QLabel("Resolution Progress")
        progress_title.setProperty("subheading", True)
        progress_layout.addWidget(progress_title)

        self._progress_resolution = ProgressBarWidget("Overall Resolution Rate", 0)
        progress_layout.addWidget(self._progress_resolution)

        self._progress_in_progress = ProgressBarWidget("In Progress", 0)
        progress_layout.addWidget(self._progress_in_progress)

        self._progress_open = ProgressBarWidget("Awaiting Action (Open)", 0)
        progress_layout.addWidget(self._progress_open)

        self._progress_draft = ProgressBarWidget("Draft Issues", 0)
        progress_layout.addWidget(self._progress_draft)

        main_layout.addWidget(progress_frame)

        # Charts Row 2: Stacked Bar Charts
        charts_row2 = QHBoxLayout()
        charts_row2.setSpacing(16)

        # Issues by Department
        dept_frame = QFrame()
        dept_frame.setProperty("card", True)
        dept_layout = QVBoxLayout(dept_frame)
        self._dept_chart = StackedBarChartWidget("Issues by Department")
        dept_layout.addWidget(self._dept_chart)
        charts_row2.addWidget(dept_frame)

        # Issues by Topic
        topic_frame = QFrame()
        topic_frame.setProperty("card", True)
        topic_layout = QVBoxLayout(topic_frame)
        self._topic_chart = StackedBarChartWidget("Issues by Topic")
        topic_layout.addWidget(self._topic_chart)
        charts_row2.addWidget(topic_frame)

        main_layout.addLayout(charts_row2)

        main_layout.addStretch()

        scroll.setWidget(content)
        splitter.addWidget(scroll)

        # Set splitter sizes (filter panel: 250px, dashboard: rest)
        splitter.setSizes([250, 950])

        layout.addWidget(splitter)

    def set_user(self, user: User):
        """Set current user and refresh data."""
        self._user = user
        self.refresh()

    def refresh(self):
        """Refresh all dashboard data including filter options."""
        if not self._user:
            self._user = self._auth.current_user

        if not self._user:
            return

        # Refresh filter options (only on full refresh, not on filter change)
        self._filter_panel.refresh_options()

        # Apply filters and update charts
        self._apply_filters()

    def _apply_filters(self):
        """Apply current filters and update dashboard charts."""
        if not self._user:
            self._user = self._auth.current_user

        if not self._user:
            return

        # Get filters and dashboard data
        filters = self._filter_panel.get_filters()
        data = self._issue_service.get_dashboard_data(self._user, filters)

        # Update KPIs
        self._kpi_total.set_value(data["total_issues"])
        self._kpi_active.set_value(data["active_issues"])
        self._kpi_high_priority.set_value(data["high_priority_open"])
        self._kpi_overdue.set_value(data["overdue"])
        self._kpi_resolution.set_value(data["resolution_rate"])

        # Update status chart
        status_colors = {s.value: CHART_COLORS[s.value] for s in Status}
        self._status_chart.set_data(data["status_distribution"], status_colors)

        # Update risk chart
        risk_colors = {r: CHART_COLORS[r] for r in ["None", "Low", "Medium", "High"]}
        self._risk_chart.set_data(data["risk_distribution"], risk_colors)

        # Update progress bars
        total = data["total_issues"]
        if total > 0:
            status_dist = data["status_distribution"]

            self._progress_resolution.set_value(data["resolution_rate"])

            in_progress_pct = status_dist.get(Status.IN_PROGRESS.value, 0) / total * 100
            self._progress_in_progress.set_value(in_progress_pct)

            open_pct = status_dist.get(Status.OPEN.value, 0) / total * 100
            self._progress_open.set_value(open_pct)

            draft_pct = status_dist.get(Status.DRAFT.value, 0) / total * 100
            self._progress_draft.set_value(draft_pct)
        else:
            self._progress_resolution.set_value(0)
            self._progress_in_progress.set_value(0)
            self._progress_open.set_value(0)
            self._progress_draft.set_value(0)

        # Update department chart
        self._dept_chart.set_data(
            data["department_distribution"],
            segment_order=Status.values(),
            color_map={s.value: CHART_COLORS[s.value] for s in Status}
        )

        # Update topic chart
        self._topic_chart.set_data(
            data["topic_distribution"],
            segment_order=Status.values(),
            color_map={s.value: CHART_COLORS[s.value] for s in Status}
        )
