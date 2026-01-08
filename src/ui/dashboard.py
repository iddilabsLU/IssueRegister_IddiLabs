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
from src.ui.widgets.charts import PieChartWidget, StackedBarChartWidget, ProgressBarWidget, CHART_COLORS, PALETTE_SEQUENCE
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

        # Charts Row 3: Issues by Owner and Identified By (Status segments)
        charts_row3 = QHBoxLayout()
        charts_row3.setSpacing(16)

        # Issues by Owner
        owner_frame = QFrame()
        owner_frame.setProperty("card", True)
        owner_layout = QVBoxLayout(owner_frame)
        self._owner_chart = StackedBarChartWidget("Issues by Owner")
        owner_layout.addWidget(self._owner_chart)
        charts_row3.addWidget(owner_frame)

        # Issues by Identified By
        identified_frame = QFrame()
        identified_frame.setProperty("card", True)
        identified_layout = QVBoxLayout(identified_frame)
        self._identified_chart = StackedBarChartWidget("Issues by Identified By")
        identified_layout.addWidget(self._identified_chart)
        charts_row3.addWidget(identified_frame)

        main_layout.addLayout(charts_row3)

        # Charts Row 4: Risk by Department and Topic
        charts_row4 = QHBoxLayout()
        charts_row4.setSpacing(16)

        # Risk by Department
        dept_risk_frame = QFrame()
        dept_risk_frame.setProperty("card", True)
        dept_risk_layout = QVBoxLayout(dept_risk_frame)
        self._dept_risk_chart = StackedBarChartWidget("Risk by Department")
        dept_risk_layout.addWidget(self._dept_risk_chart)
        charts_row4.addWidget(dept_risk_frame)

        # Risk by Topic
        topic_risk_frame = QFrame()
        topic_risk_frame.setProperty("card", True)
        topic_risk_layout = QVBoxLayout(topic_risk_frame)
        self._topic_risk_chart = StackedBarChartWidget("Risk by Topic")
        topic_risk_layout.addWidget(self._topic_risk_chart)
        charts_row4.addWidget(topic_risk_frame)

        main_layout.addLayout(charts_row4)

        # Charts Row 5: Risk by Owner and Identified By
        charts_row5 = QHBoxLayout()
        charts_row5.setSpacing(16)

        # Risk by Owner
        owner_risk_frame = QFrame()
        owner_risk_frame.setProperty("card", True)
        owner_risk_layout = QVBoxLayout(owner_risk_frame)
        self._owner_risk_chart = StackedBarChartWidget("Risk by Owner")
        owner_risk_layout.addWidget(self._owner_risk_chart)
        charts_row5.addWidget(owner_risk_frame)

        # Risk by Identified By
        identified_risk_frame = QFrame()
        identified_risk_frame.setProperty("card", True)
        identified_risk_layout = QVBoxLayout(identified_risk_frame)
        self._identified_risk_chart = StackedBarChartWidget("Risk by Identified By")
        identified_risk_layout.addWidget(self._identified_risk_chart)
        charts_row5.addWidget(identified_risk_frame)

        main_layout.addLayout(charts_row5)

        # Charts Row 6: Due Date charts
        charts_row6 = QHBoxLayout()
        charts_row6.setSpacing(16)

        # Risks by Due Date
        duedate_risk_frame = QFrame()
        duedate_risk_frame.setProperty("card", True)
        duedate_risk_layout = QVBoxLayout(duedate_risk_frame)
        self._duedate_risk_chart = StackedBarChartWidget("Risks by Due Date")
        duedate_risk_layout.addWidget(self._duedate_risk_chart)
        charts_row6.addWidget(duedate_risk_frame)

        # Topics by Due Date
        duedate_topic_frame = QFrame()
        duedate_topic_frame.setProperty("card", True)
        duedate_topic_layout = QVBoxLayout(duedate_topic_frame)
        self._duedate_topic_chart = StackedBarChartWidget("Topics by Due Date")
        duedate_topic_layout.addWidget(self._duedate_topic_chart)
        charts_row6.addWidget(duedate_topic_frame)

        main_layout.addLayout(charts_row6)

        # Charts Row 7: Aging Analysis and Overdue Breakdown
        charts_row7 = QHBoxLayout()
        charts_row7.setSpacing(16)

        # Aging Analysis (excludes Closed issues)
        aging_frame = QFrame()
        aging_frame.setProperty("card", True)
        aging_layout = QVBoxLayout(aging_frame)
        self._aging_chart = StackedBarChartWidget("Issue Aging (excl. Closed)")
        aging_layout.addWidget(self._aging_chart)
        charts_row7.addWidget(aging_frame)

        # Overdue Breakdown (excludes Closed issues)
        overdue_frame = QFrame()
        overdue_frame.setProperty("card", True)
        overdue_layout = QVBoxLayout(overdue_frame)
        self._overdue_chart = StackedBarChartWidget("Overdue Breakdown (excl. Closed)")
        overdue_layout.addWidget(self._overdue_chart)
        charts_row7.addWidget(overdue_frame)

        main_layout.addLayout(charts_row7)

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

        # Define color maps for reuse
        status_color_map = {s.value: CHART_COLORS[s.value] for s in Status}
        risk_color_map = {r: CHART_COLORS[r] for r in ["None", "Low", "Medium", "High"]}
        risk_order = ["None", "Low", "Medium", "High"]

        # Update Owner chart (Status segments) - Chart 1
        self._owner_chart.set_data(
            data["owner_distribution"],
            segment_order=Status.values(),
            color_map=status_color_map
        )

        # Update Identified By chart (Status segments) - Chart 2
        self._identified_chart.set_data(
            data["identified_by_distribution"],
            segment_order=Status.values(),
            color_map=status_color_map
        )

        # Update Department Risk chart - Chart 3
        self._dept_risk_chart.set_data(
            data["department_risk_distribution"],
            segment_order=risk_order,
            color_map=risk_color_map
        )

        # Update Topic Risk chart - Chart 4
        self._topic_risk_chart.set_data(
            data["topic_risk_distribution"],
            segment_order=risk_order,
            color_map=risk_color_map
        )

        # Update Owner Risk chart - Chart 5
        self._owner_risk_chart.set_data(
            data["owner_risk_distribution"],
            segment_order=risk_order,
            color_map=risk_color_map
        )

        # Update Identified By Risk chart - Chart 6
        self._identified_risk_chart.set_data(
            data["identified_by_risk_distribution"],
            segment_order=risk_order,
            color_map=risk_color_map
        )

        # Update DueDate Risk chart - Chart 7
        self._duedate_risk_chart.set_data(
            data["risk_by_duedate"],
            segment_order=risk_order,
            color_map=risk_color_map
        )

        # Update DueDate Topic chart - Chart 8 (dynamic colors from PALETTE_SEQUENCE)
        all_topics = data.get("all_topics", [])
        topic_color_map = {
            topic: PALETTE_SEQUENCE[i % len(PALETTE_SEQUENCE)]
            for i, topic in enumerate(sorted(all_topics))
        }
        self._duedate_topic_chart.set_data(
            data["topic_by_duedate"],
            segment_order=sorted(all_topics),
            color_map=topic_color_map
        )

        # Update Aging Analysis chart (stacked by risk, excludes Closed)
        aging_buckets = ["0-30 days", "31-60 days", "61-90 days", "91-180 days", "180+ days"]
        self._aging_chart.set_data(
            data["aging_distribution"],
            segment_order=risk_order,
            color_map=risk_color_map
        )

        # Update Overdue Breakdown chart (stacked by risk, excludes Closed)
        self._overdue_chart.set_data(
            data["overdue_breakdown"],
            segment_order=risk_order,
            color_map=risk_color_map
        )
