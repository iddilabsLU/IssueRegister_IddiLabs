"""Main application window."""

from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QStackedWidget, QPushButton, QLabel, QFrame, QMessageBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from src.services.auth import get_auth_service
from src.database.models import User


class MainWindow(QMainWindow):
    """
    Main application window with navigation.

    Contains:
    - Navigation bar (Register, Dashboard, Settings)
    - Stacked widget for views
    - User info and logout button
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self._auth = get_auth_service()
        self._views = {}

        self._setup_ui()
        self._load_views()
        self._connect_signals()

        # Start on register view
        self._navigate_to("register")

    def _setup_ui(self):
        """Set up the main window UI."""
        self.setWindowTitle("Issue Register")
        self.setMinimumSize(1200, 800)

        # Central widget
        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Header/Navigation bar
        header = self._create_header()
        main_layout.addWidget(header)

        # Content area
        self._stack = QStackedWidget()
        main_layout.addWidget(self._stack, 1)

        # Status bar
        self.statusBar().showMessage("Ready")

    def _create_header(self) -> QFrame:
        """Create the navigation header."""
        header = QFrame()
        header.setProperty("navigation", True)
        header.setFixedHeight(56)

        layout = QHBoxLayout(header)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(0)

        # App title
        title = QLabel("Issue Register")
        title.setStyleSheet("color: white; font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        layout.addSpacing(32)

        # Navigation buttons
        self._nav_buttons = {}

        nav_items = [
            ("register", "Issues"),
            ("dashboard", "Dashboard"),
            ("settings", "Settings"),
            ("iddi_labs", "IddiLabs"),
        ]

        for nav_id, label in nav_items:
            btn = QPushButton(label)
            btn.setProperty("nav", True)
            btn.setCheckable(True)
            btn.setAutoExclusive(True)
            btn.clicked.connect(lambda checked, n=nav_id: self._navigate_to(n))
            layout.addWidget(btn)
            self._nav_buttons[nav_id] = btn

        layout.addStretch()

        # User info
        self._user_label = QLabel()
        self._user_label.setStyleSheet("color: white;")
        layout.addWidget(self._user_label)

        layout.addSpacing(16)

        # Logout button
        logout_btn = QPushButton("Logout")
        logout_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: white;
                border: 1px solid rgba(255, 255, 255, 0.3);
                padding: 6px 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
            }
        """)
        logout_btn.clicked.connect(self._on_logout)
        layout.addWidget(logout_btn)

        return header

    def _load_views(self):
        """Load and add all views to the stack."""
        # Import here to avoid circular imports
        from src.ui.register import RegisterView
        from src.ui.dashboard import DashboardView
        from src.ui.settings import SettingsView
        from src.ui.iddi_labs import IddiLabsView

        # Register view
        register_view = RegisterView()
        self._stack.addWidget(register_view)
        self._views["register"] = register_view

        # Dashboard view
        dashboard_view = DashboardView()
        self._stack.addWidget(dashboard_view)
        self._views["dashboard"] = dashboard_view

        # Settings view
        settings_view = SettingsView()
        self._stack.addWidget(settings_view)
        self._views["settings"] = settings_view

        # IddiLabs view
        iddi_labs_view = IddiLabsView()
        self._stack.addWidget(iddi_labs_view)
        self._views["iddi_labs"] = iddi_labs_view

    def _connect_signals(self):
        """Connect view signals."""
        # Refresh dashboard when switching to it
        pass

    def _navigate_to(self, view_id: str):
        """
        Navigate to a specific view.

        Args:
            view_id: View identifier (register, dashboard, settings)
        """
        if view_id not in self._views:
            return

        view = self._views[view_id]
        self._stack.setCurrentWidget(view)

        # Update nav button states
        if view_id in self._nav_buttons:
            self._nav_buttons[view_id].setChecked(True)

        # Refresh view data
        if hasattr(view, "refresh"):
            view.refresh()

        # Update status
        view_names = {
            "register": "Issue Register",
            "dashboard": "Dashboard",
            "settings": "Settings",
            "iddi_labs": "IddiLabs"
        }
        self.statusBar().showMessage(f"Viewing: {view_names.get(view_id, view_id)}")

    def _on_logout(self):
        """Handle logout button click."""
        reply = QMessageBox.question(
            self,
            "Confirm Logout",
            "Are you sure you want to logout?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self._auth.logout()
            self.close()

    def set_user(self, user: User):
        """
        Set the current user and update UI.

        Args:
            user: Logged in user
        """
        self._user_label.setText(f"Logged in as: {user.username} ({user.role})")

        # Update view permissions
        for view in self._views.values():
            if hasattr(view, "set_user"):
                view.set_user(user)

    def showEvent(self, event):
        """Handle window show event."""
        super().showEvent(event)

        # Update user display
        if self._auth.current_user:
            self.set_user(self._auth.current_user)

    def closeEvent(self, event):
        """Handle window close event."""
        # Could add confirmation or cleanup here
        event.accept()
