"""Chart widgets for dashboard visualizations using QtCharts."""

from typing import Optional

from PySide6.QtWidgets import QWidget, QVBoxLayout, QSizePolicy
from PySide6.QtCharts import (
    QChart, QChartView, QPieSeries, QPieSlice,
    QBarSeries, QBarSet, QBarCategoryAxis, QValueAxis,
    QHorizontalStackedBarSeries, QAbstractBarSeries
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QColor, QFont

from src.database.models import Status


# Color palette for charts
CHART_COLORS = {
    # Status colors
    Status.DRAFT.value: QColor("#9CA3AF"),      # Gray
    Status.OPEN.value: QColor("#3B82F6"),       # Blue
    Status.IN_PROGRESS.value: QColor("#F59E0B"), # Amber
    Status.REMEDIATED.value: QColor("#10B981"),  # Green
    Status.CLOSED.value: QColor("#6B7280"),      # Dark gray

    # Risk colors
    "None": QColor("#9CA3AF"),
    "Low": QColor("#10B981"),
    "Medium": QColor("#F59E0B"),
    "High": QColor("#EF4444"),

    # Generic palette
    "primary": QColor("#2D3E50"),
    "secondary": QColor("#E6E2DA"),
}

# Sequence for generic items
PALETTE_SEQUENCE = [
    QColor("#2D3E50"),
    QColor("#3B82F6"),
    QColor("#10B981"),
    QColor("#F59E0B"),
    QColor("#EF4444"),
    QColor("#8B5CF6"),
    QColor("#EC4899"),
    QColor("#06B6D4"),
]


class PieChartWidget(QWidget):
    """
    Pie/donut chart widget for distribution visualization.

    Usage:
        chart = PieChartWidget("Status Distribution")
        chart.set_data({"Open": 10, "Closed": 5})
    """

    def __init__(self, title: str = "", donut: bool = False, parent=None):
        """
        Initialize pie chart.

        Args:
            title: Chart title
            donut: If True, create donut chart instead of pie
            parent: Parent widget
        """
        super().__init__(parent)

        self._title = title
        self._donut = donut

        self._setup_ui()

    def _setup_ui(self):
        """Set up the chart UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Create chart
        self._chart = QChart()
        self._chart.setTitle(self._title)
        self._chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)

        # Legend configuration - position on right for vertical display
        legend = self._chart.legend()
        legend.setVisible(True)
        legend.setAlignment(Qt.AlignmentFlag.AlignRight)
        # Smaller font for legend to fit more text
        legend_font = QFont()
        legend_font.setPointSize(9)
        legend.setFont(legend_font)

        # Chart font
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(12)
        self._chart.setTitleFont(title_font)

        # Create series
        self._series = QPieSeries()
        if self._donut:
            self._series.setHoleSize(0.4)
        self._chart.addSeries(self._series)

        # Chart view
        self._chart_view = QChartView(self._chart)
        self._chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._chart_view.setMinimumHeight(280)

        layout.addWidget(self._chart_view)

    def set_data(self, data: dict[str, int], color_map: Optional[dict] = None):
        """
        Set chart data.

        Args:
            data: Dictionary of label -> value
            color_map: Optional dictionary of label -> QColor
        """
        self._series.clear()

        total = sum(data.values())
        if total == 0:
            return

        for i, (label, value) in enumerate(data.items()):
            slice_ = self._series.append(label, value)

            # Set color
            if color_map and label in color_map:
                color = color_map[label]
            elif label in CHART_COLORS:
                color = CHART_COLORS[label]
            else:
                color = PALETTE_SEQUENCE[i % len(PALETTE_SEQUENCE)]

            slice_.setColor(color)
            slice_.setBorderColor(color.darker(110))

            # Show label with percentage
            pct = value / total * 100
            slice_.setLabel(f"{label}: {value} ({pct:.0f}%)")
            slice_.setLabelVisible(pct >= 5)  # Only show if >= 5%

    def set_title(self, title: str):
        """Update chart title."""
        self._title = title
        self._chart.setTitle(title)

    def clear(self):
        """Clear chart data."""
        self._series.clear()


class StackedBarChartWidget(QWidget):
    """
    Horizontal stacked bar chart for category breakdown.

    Usage:
        chart = StackedBarChartWidget("Issues by Department")
        chart.set_data({
            "IT": {"Open": 5, "Closed": 3},
            "HR": {"Open": 2, "Closed": 4}
        })
    """

    def __init__(self, title: str = "", parent=None):
        """
        Initialize stacked bar chart.

        Args:
            title: Chart title
            parent: Parent widget
        """
        super().__init__(parent)

        self._title = title

        self._setup_ui()

    def _setup_ui(self):
        """Set up the chart UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Create chart
        self._chart = QChart()
        self._chart.setTitle(self._title)
        self._chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)

        # Legend configuration - position on right for vertical display
        legend = self._chart.legend()
        legend.setVisible(True)
        legend.setAlignment(Qt.AlignmentFlag.AlignRight)
        # Smaller font for legend to fit more text
        legend_font = QFont()
        legend_font.setPointSize(9)
        legend.setFont(legend_font)

        # Chart font
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(12)
        self._chart.setTitleFont(title_font)

        # Chart view
        self._chart_view = QChartView(self._chart)
        self._chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._chart_view.setMinimumHeight(300)

        layout.addWidget(self._chart_view)

    def set_data(
        self,
        data: dict[str, dict[str, int]],
        segment_order: Optional[list[str]] = None,
        color_map: Optional[dict] = None
    ):
        """
        Set chart data.

        Args:
            data: Dictionary of category -> {segment: value}
            segment_order: Optional list defining segment order
            color_map: Optional dictionary of segment -> QColor
        """
        self._chart.removeAllSeries()

        # Remove old axes
        for axis in self._chart.axes():
            self._chart.removeAxis(axis)

        if not data:
            return

        categories = list(data.keys())

        # Determine all segments
        all_segments = set()
        for cat_data in data.values():
            all_segments.update(cat_data.keys())

        if segment_order:
            segments = [s for s in segment_order if s in all_segments]
        else:
            segments = sorted(all_segments)

        # Create series
        series = QHorizontalStackedBarSeries()

        for i, segment in enumerate(segments):
            bar_set = QBarSet(segment)

            # Set color
            if color_map and segment in color_map:
                color = color_map[segment]
            elif segment in CHART_COLORS:
                color = CHART_COLORS[segment]
            else:
                color = PALETTE_SEQUENCE[i % len(PALETTE_SEQUENCE)]

            bar_set.setColor(color)
            bar_set.setBorderColor(color.darker(110))

            # Set white label color for visibility inside bars
            bar_set.setLabelColor(QColor("white"))
            label_font = QFont()
            label_font.setPointSize(9)
            label_font.setBold(True)
            bar_set.setLabelFont(label_font)

            # Add values for each category
            for category in categories:
                value = data[category].get(segment, 0)
                bar_set.append(value)

            series.append(bar_set)

        # Enable labels inside bars
        series.setLabelsVisible(True)
        series.setLabelsPosition(QAbstractBarSeries.LabelsPosition.LabelsCenter)

        self._chart.addSeries(series)

        # Category axis (Y)
        axis_y = QBarCategoryAxis()
        axis_y.append(categories)
        self._chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
        series.attachAxis(axis_y)

        # Value axis (X)
        axis_x = QValueAxis()
        max_value = max(
            sum(cat_data.values())
            for cat_data in data.values()
        ) if data else 10
        axis_x.setRange(0, max_value * 1.1)
        axis_x.setLabelFormat("%d")
        self._chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
        series.attachAxis(axis_x)

    def set_title(self, title: str):
        """Update chart title."""
        self._title = title
        self._chart.setTitle(title)

    def clear(self):
        """Clear chart data."""
        self._chart.removeAllSeries()


class ProgressBarWidget(QWidget):
    """
    Custom progress bar with label.

    Usage:
        bar = ProgressBarWidget("Resolution Rate", 75, suffix="%")
    """

    def __init__(
        self,
        label: str = "",
        value: float = 0,
        suffix: str = "%",
        parent=None
    ):
        """
        Initialize progress bar.

        Args:
            label: Description text
            value: Progress value (0-100)
            suffix: Suffix for value display
            parent: Parent widget
        """
        super().__init__(parent)

        from PySide6.QtWidgets import QProgressBar, QLabel, QHBoxLayout

        self._label = label
        self._suffix = suffix

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._label_widget = QLabel(label)
        self._label_widget.setMinimumWidth(150)
        layout.addWidget(self._label_widget)

        self._progress_bar = QProgressBar()
        self._progress_bar.setMinimum(0)
        self._progress_bar.setMaximum(100)
        self._progress_bar.setTextVisible(False)
        layout.addWidget(self._progress_bar, 1)

        self._value_label = QLabel()
        self._value_label.setMinimumWidth(50)
        self._value_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self._value_label)

        self.set_value(value)

    def set_value(self, value: float):
        """
        Update progress value.

        Args:
            value: Progress value (0-100)
        """
        self._progress_bar.setValue(int(value))
        self._value_label.setText(f"{value:.1f}{self._suffix}")

    def set_label(self, label: str):
        """Update label text."""
        self._label = label
        self._label_widget.setText(label)
