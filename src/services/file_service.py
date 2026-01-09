"""File attachment service for managing issue supporting documents."""

import os
import platform
import shutil
import subprocess
import uuid
from pathlib import Path
from typing import Optional

from src.database.connection import DatabaseConnection


class FileService:
    """
    Handles file attachment operations for issues.

    Features:
    - Add files to issues (copy to attachments folder)
    - Open files (copy to Downloads, open with system app)
    - Remove files (move to _deleted folder)
    - Handle filename conflicts with numbering
    """

    ATTACHMENTS_FOLDER = "attachments"
    DELETED_FOLDER = "_deleted"
    STAGING_FOLDER = "_staging"
    MAX_FILENAME_LENGTH = 200  # Windows limit is 255, leave room for path

    def __init__(self):
        """Initialize the file service."""
        pass

    def get_attachments_root(self) -> Path:
        """
        Get the root attachments folder path (next to database).

        Returns:
            Path to attachments folder
        """
        db_path = DatabaseConnection.get_instance().db_path
        return db_path.parent / self.ATTACHMENTS_FOLDER

    def get_issue_folder(self, issue_id: int) -> Path:
        """
        Get the attachment folder for a specific issue.

        Args:
            issue_id: The issue ID

        Returns:
            Path to issue's attachment folder
        """
        return self.get_attachments_root() / str(issue_id)

    def get_deleted_folder(self, issue_id: int) -> Path:
        """
        Get the deleted files folder for a specific issue.

        Args:
            issue_id: The issue ID

        Returns:
            Path to issue's deleted files folder
        """
        return self.get_attachments_root() / self.DELETED_FOLDER / str(issue_id)

    def get_staging_folder(self, session_id: str) -> Path:
        """
        Get the staging folder for a new issue session.

        Args:
            session_id: UUID for the session

        Returns:
            Path to staging folder
        """
        return self.get_attachments_root() / self.STAGING_FOLDER / session_id

    def create_staging_session(self) -> str:
        """
        Create a new staging session for a new issue.

        Returns:
            Session UUID string
        """
        session_id = str(uuid.uuid4())
        staging_folder = self.get_staging_folder(session_id)
        staging_folder.mkdir(parents=True, exist_ok=True)
        return session_id

    def cleanup_staging_session(self, session_id: str) -> None:
        """
        Clean up a staging session (on cancel or after migration).

        Args:
            session_id: Session UUID to clean up
        """
        staging_folder = self.get_staging_folder(session_id)
        if staging_folder.exists():
            shutil.rmtree(staging_folder, ignore_errors=True)

    def migrate_staging_to_issue(
        self,
        session_id: str,
        issue_id: int
    ) -> tuple[list[str], list[str]]:
        """
        Move files from staging to issue folder after issue creation.

        Args:
            session_id: Staging session UUID
            issue_id: New issue ID

        Returns:
            Tuple of (migrated_filenames, errors)
        """
        staging_folder = self.get_staging_folder(session_id)
        issue_folder = self.get_issue_folder(issue_id)

        migrated = []
        errors = []

        if not staging_folder.exists():
            return migrated, errors

        issue_folder.mkdir(parents=True, exist_ok=True)

        for file_path in staging_folder.iterdir():
            if file_path.is_file():
                dest_name = self._get_unique_filename(
                    issue_folder, file_path.name
                )
                dest_path = issue_folder / dest_name
                try:
                    shutil.move(str(file_path), str(dest_path))
                    migrated.append(dest_name)
                except Exception as e:
                    errors.append(f"Failed to move {file_path.name}: {e}")

        # Clean up empty staging folder
        self.cleanup_staging_session(session_id)

        return migrated, errors

    def _sanitize_filename(self, filename: str) -> str:
        """
        Sanitize filename by removing/replacing problematic characters.

        Args:
            filename: Original filename

        Returns:
            Sanitized filename
        """
        # Characters not allowed in Windows filenames
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')

        # Remove leading/trailing spaces and dots
        filename = filename.strip(' .')

        # Truncate if too long
        if len(filename) > self.MAX_FILENAME_LENGTH:
            name, ext = os.path.splitext(filename)
            max_name_len = self.MAX_FILENAME_LENGTH - len(ext)
            filename = name[:max_name_len] + ext

        # If filename is empty after sanitization, use a default
        if not filename:
            filename = "unnamed_file"

        return filename

    def _get_unique_filename(self, folder: Path, filename: str) -> str:
        """
        Get a unique filename by adding numbers if conflict exists.

        Args:
            folder: Target folder path
            filename: Desired filename

        Returns:
            Unique filename (e.g., "report (2).pdf")
        """
        filename = self._sanitize_filename(filename)

        if not (folder / filename).exists():
            return filename

        name, ext = os.path.splitext(filename)
        counter = 2

        while True:
            new_name = f"{name} ({counter}){ext}"
            if not (folder / new_name).exists():
                return new_name
            counter += 1
            # Safety limit to prevent infinite loop
            if counter > 10000:
                raise ValueError(f"Too many files with name: {filename}")

    def add_file(
        self,
        source_path: str,
        issue_id: Optional[int] = None,
        session_id: Optional[str] = None
    ) -> tuple[Optional[str], str]:
        """
        Add a file as an attachment (copy to attachments folder).

        Args:
            source_path: Full path to source file
            issue_id: Issue ID (for existing issues)
            session_id: Staging session ID (for new issues)

        Returns:
            Tuple of (filename_stored, error_message)
        """
        if not issue_id and not session_id:
            return None, "Either issue_id or session_id must be provided"

        source = Path(source_path)

        if not source.exists():
            return None, f"Source file not found: {source_path}"

        if not source.is_file():
            return None, f"Not a file: {source_path}"

        # Determine target folder
        if issue_id:
            target_folder = self.get_issue_folder(issue_id)
        else:
            target_folder = self.get_staging_folder(session_id)

        target_folder.mkdir(parents=True, exist_ok=True)

        # Get unique filename
        dest_name = self._get_unique_filename(target_folder, source.name)
        dest_path = target_folder / dest_name

        try:
            shutil.copy2(str(source), str(dest_path))
            return dest_name, ""
        except PermissionError:
            return None, f"Permission denied copying file: {source.name}"
        except Exception as e:
            return None, f"Failed to copy file: {str(e)}"

    def resolve_file_path(
        self,
        filename: str,
        issue_id: int
    ) -> tuple[Optional[Path], str]:
        """
        Resolve a filename to its full path, handling legacy absolute paths.

        Args:
            filename: Filename or legacy absolute path from database
            issue_id: Issue ID

        Returns:
            Tuple of (resolved_path, error_message)
        """
        # Check if it's a legacy absolute path (contains path separators)
        if '/' in filename or '\\' in filename:
            legacy_path = Path(filename)
            if legacy_path.exists():
                return legacy_path, ""
            return None, f"Legacy file not found: {filename}"

        # Look in issue's attachment folder
        file_path = self.get_issue_folder(issue_id) / filename
        if file_path.exists():
            return file_path, ""

        return None, f"File not found: {filename}"

    def get_downloads_folder(self) -> Path:
        """
        Get the user's Downloads folder path.

        Returns:
            Path to Downloads folder
        """
        if platform.system() == "Windows":
            # Use shell API for proper Windows Downloads folder
            try:
                import ctypes.wintypes
                CSIDL_DOWNLOADS = 0x27
                buf = ctypes.create_unicode_buffer(ctypes.wintypes.MAX_PATH)
                ctypes.windll.shell32.SHGetFolderPathW(
                    None, CSIDL_DOWNLOADS, None, 0, buf
                )
                downloads = Path(buf.value)
                if downloads.exists():
                    return downloads
            except Exception:
                pass

        # Fallback: user home / Downloads
        downloads = Path.home() / "Downloads"
        if not downloads.exists():
            downloads.mkdir(parents=True, exist_ok=True)
        return downloads

    def open_file(
        self,
        filename: str,
        issue_id: int
    ) -> tuple[Optional[Path], str]:
        """
        Open a file by copying to Downloads and opening with system app.

        Args:
            filename: Filename or legacy path from database
            issue_id: Issue ID

        Returns:
            Tuple of (downloaded_path, error_message)
        """
        # Resolve source file
        source_path, error = self.resolve_file_path(filename, issue_id)
        if error:
            return None, error

        # Get downloads folder
        downloads = self.get_downloads_folder()
        if not downloads.exists():
            return None, "Downloads folder not found"

        # Check if writable
        if not os.access(str(downloads), os.W_OK):
            return None, "Downloads folder is not writable"

        # Copy with unique filename
        dest_name = self._get_unique_filename(downloads, source_path.name)
        dest_path = downloads / dest_name

        try:
            shutil.copy2(str(source_path), str(dest_path))
        except Exception as e:
            return None, f"Failed to copy to Downloads: {str(e)}"

        # Open with system default application
        try:
            if platform.system() == "Windows":
                os.startfile(str(dest_path))
            elif platform.system() == "Darwin":  # macOS
                subprocess.run(["open", str(dest_path)], check=True)
            else:  # Linux
                subprocess.run(["xdg-open", str(dest_path)], check=True)
        except Exception as e:
            # File copied but couldn't open - partial success
            return dest_path, f"File copied to Downloads but couldn't open: {e}"

        return dest_path, ""

    def remove_file(
        self,
        filename: str,
        issue_id: int
    ) -> tuple[bool, str]:
        """
        Remove a file by moving to _deleted folder.

        Args:
            filename: Filename from database
            issue_id: Issue ID

        Returns:
            Tuple of (success, error_message)
        """
        # Resolve source file
        source_path, error = self.resolve_file_path(filename, issue_id)
        if error:
            # File doesn't exist - still "remove" successfully from database
            return True, ""

        # Create deleted folder
        deleted_folder = self.get_deleted_folder(issue_id)
        deleted_folder.mkdir(parents=True, exist_ok=True)

        # Get unique filename in deleted folder
        dest_name = self._get_unique_filename(deleted_folder, source_path.name)
        dest_path = deleted_folder / dest_name

        try:
            shutil.move(str(source_path), str(dest_path))
            return True, ""
        except Exception as e:
            return False, f"Failed to move file to deleted: {str(e)}"

    def get_attachment_file_info(
        self,
        filename: str,
        issue_id: int
    ) -> dict:
        """
        Get information about an attached file.

        Args:
            filename: Filename from database
            issue_id: Issue ID

        Returns:
            Dictionary with file info (exists, size, display_name, is_legacy)
        """
        is_legacy = '/' in filename or '\\' in filename
        display_name = Path(filename).name if is_legacy else filename

        resolved, _ = self.resolve_file_path(filename, issue_id)

        if resolved and resolved.exists():
            return {
                "exists": True,
                "size": resolved.stat().st_size,
                "display_name": display_name,
                "is_legacy": is_legacy,
                "full_path": str(resolved),
            }

        return {
            "exists": False,
            "size": 0,
            "display_name": display_name,
            "is_legacy": is_legacy,
            "full_path": None,
        }


# Singleton instance
_file_service: Optional[FileService] = None


def get_file_service() -> FileService:
    """Get the singleton FileService instance."""
    global _file_service
    if _file_service is None:
        _file_service = FileService()
    return _file_service


def reset_file_service() -> None:
    """Reset the singleton instance (for testing)."""
    global _file_service
    _file_service = None
