"""Issue Register - Main Application Entry Point."""

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication, QMessageBox, QDialog
from PySide6.QtCore import Qt

from src.database.connection import DatabaseConnection
from src.database.migrations import setup_database_with_demo_data, database_needs_init, ensure_all_tables_exist
from src.services.auth import get_auth_service, reset_auth_service
from src.services.config import get_saved_database_path, set_saved_database_path
from src.ui.main_window import MainWindow
from src.ui.login import LoginDialog, DatabaseSelectionDialog


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


def initialize_database(db_path: str) -> bool:
    """
    Initialize the database at the specified path and run migrations.

    Args:
        db_path: Path to the database file

    Returns:
        True if successful, False otherwise
    """
    try:
        # Reset any existing connection
        DatabaseConnection.reset_instance()

        # Connect to the specified database
        DatabaseConnection.get_instance(db_path)

        if database_needs_init():
            setup_database_with_demo_data()
        else:
            # Ensure all tables exist for existing databases
            ensure_all_tables_exist()

        return True
    except Exception:
        return False


def select_database(current_path: str = None, error_message: str = None) -> str:
    """
    Show database selection dialog and return selected path.

    Args:
        current_path: Current database path to show
        error_message: Error message to display

    Returns:
        Selected database path, or None if user cancelled
    """
    dialog = DatabaseSelectionDialog(
        current_path=current_path,
        error_message=error_message
    )

    if dialog.exec() == QDialog.DialogCode.Accepted:
        return dialog.get_selected_path()

    return None


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
        # Step 1: Get database path (from config or user selection)
        db_path = get_saved_database_path()
        error_message = None

        # Check if saved path is valid
        if db_path:
            db_file = Path(db_path)
            if not db_file.exists() and not db_file.parent.exists():
                error_message = "Previously saved database location is no longer accessible."
                db_path = None

        # If no valid path, show selection dialog
        if not db_path:
            db_path = select_database(error_message=error_message)
            if not db_path:
                # User cancelled
                return 0

        # Step 2: Initialize database
        if not initialize_database(db_path):
            # Database initialization failed, let user select different location
            db_path = select_database(
                current_path=db_path,
                error_message="Failed to connect to database. Please select a different location."
            )
            if not db_path:
                return 0
            if not initialize_database(db_path):
                QMessageBox.critical(
                    None,
                    "Database Error",
                    "Failed to initialize database. Please check the location and try again."
                )
                return 1

        # Save the working path
        set_saved_database_path(db_path)

        # Step 3: Handle authentication
        while True:
            # Reset auth service to pick up new database
            reset_auth_service()
            auth = get_auth_service()

            if auth.is_auth_enabled:
                # Show login dialog
                login_dialog = LoginDialog()

                # Track if user wants to change database
                change_database_requested = False

                def on_change_database():
                    nonlocal change_database_requested
                    change_database_requested = True

                login_dialog.database_change_requested.connect(on_change_database)

                result = login_dialog.exec()

                if change_database_requested:
                    # User wants to change database
                    new_path = select_database(current_path=db_path)
                    if new_path and new_path != db_path:
                        db_path = new_path
                        if not initialize_database(db_path):
                            QMessageBox.critical(
                                None,
                                "Database Error",
                                "Failed to connect to the selected database."
                            )
                            continue
                        set_saved_database_path(db_path)
                    # Loop back to show login for new database
                    continue

                if result != LoginDialog.DialogCode.Accepted:
                    # User cancelled login
                    return 0
            else:
                # Auth disabled - login as admin
                auth.login_as_admin()

            # Successfully authenticated, break out of loop
            break

        # Step 4: Create and show main window
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
