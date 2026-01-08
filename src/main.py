"""Issue Register - Main Application Entry Point."""

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import Qt

from src.database.connection import DatabaseConnection
from src.database.migrations import setup_database_with_demo_data, database_needs_init
from src.services.auth import get_auth_service
from src.ui.main_window import MainWindow
from src.ui.login import LoginDialog


def get_resource_path(relative_path: str) -> Path:
    """
    Get the correct path to a resource file.

    Works both in development and when bundled with PyInstaller.
    PyInstaller extracts files to a temp folder and sets sys._MEIPASS.
    """
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        # Running as bundled executable (PyInstaller)
        base_path = Path(sys._MEIPASS) / "src"
    else:
        # Running in development
        base_path = Path(__file__).parent

    return base_path / relative_path


def load_stylesheet() -> str:
    """Load the application stylesheet."""
    style_path = get_resource_path("resources/styles.qss")

    if style_path.exists():
        with open(style_path, "r", encoding="utf-8") as f:
            return f.read()

    return ""


def initialize_database():
    """Initialize the database and run migrations."""
    db = DatabaseConnection.get_instance()

    if database_needs_init():
        setup_database_with_demo_data()


def main():
    """Main application entry point."""
    # Enable high DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    # Create application
    app = QApplication(sys.argv)
    app.setApplicationName("Issue Register")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("IDDI Labs")

    # Load stylesheet
    stylesheet = load_stylesheet()
    if stylesheet:
        app.setStyleSheet(stylesheet)

    try:
        # Initialize database
        initialize_database()

        # Get auth service
        auth = get_auth_service()

        # Check if authentication is required
        if auth.is_auth_enabled:
            # Show login dialog
            login_dialog = LoginDialog()
            if login_dialog.exec() != LoginDialog.DialogCode.Accepted:
                # User cancelled login
                return 0
        else:
            # Auth disabled - login as admin
            auth.login_as_admin()

        # Create and show main window
        main_window = MainWindow()
        main_window.set_user(auth.current_user)
        main_window.show()

        # Run application
        return app.exec()

    except Exception as e:
        QMessageBox.critical(
            None,
            "Application Error",
            f"An error occurred while starting the application:\n\n{str(e)}"
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
