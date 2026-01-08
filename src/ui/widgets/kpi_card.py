"""KPI Card widget for dashboard metrics display."""

from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel
from PySide6.QtCore import Qt


class KPICard(QFrame):
    """
    A card widget displaying a single KPI metric.

    Usage:
        card = KPICard("Total Issues", 42)
        card.set_value(50)  # Update value
    """

    def __init__(
        self,
        title: str,
        value: int | float | str = 0,
        suffix: str = "",
        priority: str = "",
        parent=None
    ):
        """
        Initialize KPI card.

        Args:
            title: Label describing the metric
            value: Numeric or string value to display
            suffix: Optional suffix (e.g., "%")
            priority: Optional priority level ("high", "medium", "low") for styling
            parent: Parent widget
        """
        super().__init__(parent)

        self._title = title
        self._suffix = suffix
        self._priority = priority

        self._setup_ui()
        self.set_value(value)

    def _setup_ui(self):
        """Set up the card UI."""
        self.setProperty("kpi", True)
        self.setMinimumWidth(150)
        self.setMinimumHeight(110)  # Increased for text visibility

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(6)

        # Title label with word wrap
        self._title_label = QLabel(self._title)
        self._title_label.setProperty("kpi-label", True)
        self._title_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self._title_label.setWordWrap(True)
        self._title_label.setMinimumHeight(32)  # Space for 2 lines if needed
        layout.addWidget(self._title_label)

        # Value label - allow larger numbers
        self._value_label = QLabel("0")
        self._value_label.setProperty("kpi-value", True)
        self._value_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self._value_label.setMinimumWidth(80)  # Ensure space for large numbers
        if self._priority:
            self._value_label.setProperty("priority", self._priority)
        layout.addWidget(self._value_label)

        layout.addStretch()

    def set_value(self, value: int | float | str):
        """
        Update the displayed value.

        Args:
            value: New value to display
        """
        if isinstance(value, float):
            display_text = f"{value:.1f}{self._suffix}"
        else:
            display_text = f"{value}{self._suffix}"

        self._value_label.setText(display_text)

    def set_title(self, title: str):
        """Update the card title."""
        self._title = title
        self._title_label.setText(title)

    def set_priority(self, priority: str):
        """
        Update the priority styling.

        Args:
            priority: "high", "medium", "low", or "" for none
        """
        self._priority = priority
        self._value_label.setProperty("priority", priority)
        # Refresh style
        self._value_label.style().unpolish(self._value_label)
        self._value_label.style().polish(self._value_label)

    @property
    def value_label(self) -> QLabel:
        """Get the value label widget."""
        return self._value_label

    @property
    def title_label(self) -> QLabel:
        """Get the title label widget."""
        return self._title_label
