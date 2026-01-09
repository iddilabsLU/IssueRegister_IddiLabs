"""Tests for file service."""

import os
import tempfile
from pathlib import Path

import pytest

from src.services.file_service import FileService, get_file_service, reset_file_service


@pytest.fixture
def file_service(temp_db):
    """Create a FileService for testing."""
    reset_file_service()
    service = FileService()

    # Clean up attachments folder from previous tests
    attachments_root = service.get_attachments_root()
    if attachments_root.exists():
        import shutil
        shutil.rmtree(attachments_root, ignore_errors=True)

    return service


@pytest.fixture
def sample_file():
    """Create a temporary sample file for testing."""
    fd, path = tempfile.mkstemp(suffix=".txt")
    os.write(fd, b"Test file content")
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture
def sample_pdf():
    """Create a temporary PDF-like file for testing."""
    fd, path = tempfile.mkstemp(suffix=".pdf")
    os.write(fd, b"Fake PDF content for testing")
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.unlink(path)


class TestFilenameSanitization:
    """Test filename sanitization."""

    def test_sanitize_removes_invalid_chars(self, file_service):
        """Invalid characters are replaced with underscores."""
        result = file_service._sanitize_filename('file<>:"/\\|?*.txt')
        assert '<' not in result
        assert '>' not in result
        assert ':' not in result
        assert '"' not in result
        assert '/' not in result
        assert '\\' not in result
        assert '|' not in result
        assert '?' not in result
        assert '*' not in result

    def test_sanitize_truncates_long_names(self, file_service):
        """Long filenames are truncated while preserving extension."""
        long_name = "a" * 300 + ".txt"
        result = file_service._sanitize_filename(long_name)
        assert len(result) <= file_service.MAX_FILENAME_LENGTH
        assert result.endswith(".txt")

    def test_sanitize_strips_spaces_and_dots(self, file_service):
        """Leading/trailing spaces and dots are removed."""
        result = file_service._sanitize_filename("  ..filename..  ")
        assert not result.startswith(' ')
        assert not result.startswith('.')
        assert not result.endswith(' ')
        assert not result.endswith('.')

    def test_sanitize_empty_returns_default(self, file_service):
        """Empty filename after sanitization returns default name."""
        result = file_service._sanitize_filename("...")
        assert result == "unnamed_file"


class TestUniqueFilename:
    """Test unique filename generation."""

    def test_unique_no_conflict(self, file_service, temp_db):
        """Returns original name when no conflict exists."""
        folder = file_service.get_attachments_root()
        folder.mkdir(parents=True, exist_ok=True)
        result = file_service._get_unique_filename(folder, "report.pdf")
        assert result == "report.pdf"

    def test_unique_with_conflict(self, file_service, temp_db):
        """Returns numbered name when conflict exists."""
        folder = file_service.get_attachments_root()
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "report.pdf").touch()

        result = file_service._get_unique_filename(folder, "report.pdf")
        assert result == "report (2).pdf"

    def test_unique_multiple_conflicts(self, file_service, temp_db):
        """Handles multiple existing files with same base name."""
        folder = file_service.get_attachments_root()
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "report.pdf").touch()
        (folder / "report (2).pdf").touch()
        (folder / "report (3).pdf").touch()

        result = file_service._get_unique_filename(folder, "report.pdf")
        assert result == "report (4).pdf"


class TestStagingSession:
    """Test staging session management."""

    def test_create_staging_session(self, file_service, temp_db):
        """Creates staging folder and returns UUID."""
        session_id = file_service.create_staging_session()

        assert session_id is not None
        assert len(session_id) == 36  # UUID format
        assert file_service.get_staging_folder(session_id).exists()

    def test_cleanup_staging_session(self, file_service, temp_db, sample_file):
        """Cleans up staging folder and files."""
        session_id = file_service.create_staging_session()
        file_service.add_file(sample_file, session_id=session_id)

        file_service.cleanup_staging_session(session_id)

        assert not file_service.get_staging_folder(session_id).exists()

    def test_cleanup_nonexistent_session_no_error(self, file_service, temp_db):
        """Cleaning up non-existent session doesn't raise error."""
        file_service.cleanup_staging_session("nonexistent-session-id")
        # Should not raise


class TestAddFile:
    """Test adding files to issues."""

    def test_add_file_to_issue(self, file_service, temp_db, sample_file):
        """File is copied to issue folder."""
        filename, error = file_service.add_file(sample_file, issue_id=1)

        assert error == ""
        assert filename is not None

        expected_path = file_service.get_issue_folder(1) / filename
        assert expected_path.exists()

    def test_add_file_to_staging(self, file_service, temp_db, sample_file):
        """File is copied to staging folder for new issues."""
        session_id = file_service.create_staging_session()
        filename, error = file_service.add_file(sample_file, session_id=session_id)

        assert error == ""
        assert filename is not None

        expected_path = file_service.get_staging_folder(session_id) / filename
        assert expected_path.exists()

    def test_add_nonexistent_file(self, file_service, temp_db):
        """Returns error for non-existent source file."""
        filename, error = file_service.add_file(
            "/nonexistent/path/file.pdf",
            issue_id=1
        )

        assert filename is None
        assert "not found" in error.lower()

    def test_add_file_requires_id_or_session(self, file_service, temp_db, sample_file):
        """Returns error if neither issue_id nor session_id provided."""
        filename, error = file_service.add_file(sample_file)

        assert filename is None
        assert "must be provided" in error.lower()

    def test_add_file_handles_duplicate_names(self, file_service, temp_db, sample_file):
        """Adds numbered suffix for duplicate filenames."""
        # Add same file twice
        filename1, _ = file_service.add_file(sample_file, issue_id=1)
        filename2, _ = file_service.add_file(sample_file, issue_id=1)

        assert filename1 != filename2
        assert "(2)" in filename2


class TestMigrateStagingToIssue:
    """Test migrating files from staging to issue folder."""

    def test_migrate_staging_to_issue(self, file_service, temp_db, sample_file):
        """Files are moved from staging to issue folder."""
        session_id = file_service.create_staging_session()
        file_service.add_file(sample_file, session_id=session_id)

        migrated, errors = file_service.migrate_staging_to_issue(session_id, 1)

        assert len(errors) == 0
        assert len(migrated) == 1

        # Staging folder should be cleaned up
        assert not file_service.get_staging_folder(session_id).exists()

        # File should be in issue folder
        assert (file_service.get_issue_folder(1) / migrated[0]).exists()

    def test_migrate_multiple_files(self, file_service, temp_db, sample_file, sample_pdf):
        """Multiple files are migrated successfully."""
        session_id = file_service.create_staging_session()
        file_service.add_file(sample_file, session_id=session_id)
        file_service.add_file(sample_pdf, session_id=session_id)

        migrated, errors = file_service.migrate_staging_to_issue(session_id, 1)

        assert len(errors) == 0
        assert len(migrated) == 2

    def test_migrate_empty_staging(self, file_service, temp_db):
        """Migrating empty/nonexistent staging returns empty lists."""
        migrated, errors = file_service.migrate_staging_to_issue("nonexistent", 1)

        assert migrated == []
        assert errors == []


class TestResolveFilePath:
    """Test file path resolution."""

    def test_resolve_new_format(self, file_service, temp_db, sample_file):
        """Resolves new format (just filename)."""
        filename, _ = file_service.add_file(sample_file, issue_id=1)

        resolved, error = file_service.resolve_file_path(filename, issue_id=1)

        assert error == ""
        assert resolved is not None
        assert resolved.exists()

    def test_resolve_legacy_format(self, file_service, temp_db, sample_file):
        """Resolves legacy format (full path) if file exists."""
        resolved, error = file_service.resolve_file_path(sample_file, issue_id=1)

        assert error == ""
        assert resolved is not None
        assert resolved.exists()

    def test_resolve_missing_file(self, file_service, temp_db):
        """Returns error for missing file."""
        resolved, error = file_service.resolve_file_path("nonexistent.pdf", issue_id=1)

        assert resolved is None
        assert "not found" in error.lower()

    def test_resolve_missing_legacy_file(self, file_service, temp_db):
        """Returns error for missing legacy file path."""
        resolved, error = file_service.resolve_file_path(
            "C:\\nonexistent\\path\\file.pdf",
            issue_id=1
        )

        assert resolved is None
        assert "not found" in error.lower()


class TestRemoveFile:
    """Test file removal."""

    def test_remove_file_moves_to_deleted(self, file_service, temp_db, sample_file):
        """Removed file is moved to _deleted folder."""
        filename, _ = file_service.add_file(sample_file, issue_id=1)

        success, error = file_service.remove_file(filename, issue_id=1)

        assert success
        assert error == ""

        # File should not be in issue folder
        assert not (file_service.get_issue_folder(1) / filename).exists()

        # File should be in deleted folder
        deleted_files = list(file_service.get_deleted_folder(1).iterdir())
        assert len(deleted_files) == 1

    def test_remove_missing_file_succeeds(self, file_service, temp_db):
        """Removing a missing file succeeds (for database cleanup)."""
        success, error = file_service.remove_file("nonexistent.pdf", issue_id=1)

        assert success
        assert error == ""

    def test_remove_preserves_filename(self, file_service, temp_db, sample_file):
        """Removed file keeps its original name in deleted folder."""
        filename, _ = file_service.add_file(sample_file, issue_id=1)

        file_service.remove_file(filename, issue_id=1)

        deleted_folder = file_service.get_deleted_folder(1)
        deleted_files = [f.name for f in deleted_folder.iterdir()]
        assert filename in deleted_files

    def test_remove_handles_duplicate_names(self, file_service, temp_db, sample_file, sample_pdf):
        """Multiple removals of same-named files get numbered."""
        # Add and remove same-named file twice
        filename1, _ = file_service.add_file(sample_file, issue_id=1)
        file_service.remove_file(filename1, issue_id=1)

        filename2, _ = file_service.add_file(sample_file, issue_id=1)
        file_service.remove_file(filename2, issue_id=1)

        deleted_folder = file_service.get_deleted_folder(1)
        deleted_files = list(deleted_folder.iterdir())
        assert len(deleted_files) == 2


class TestOpenFile:
    """Test file opening functionality."""

    def test_open_file_copies_to_downloads(self, file_service, temp_db, sample_file):
        """Opening file copies it to Downloads folder."""
        filename, _ = file_service.add_file(sample_file, issue_id=1)

        # Note: We can't easily test the actual opening, but we can test the copy
        downloaded_path, error = file_service.open_file(filename, issue_id=1)

        # File might fail to open if no default app, but copy should work
        assert downloaded_path is not None
        assert downloaded_path.exists()

        # Cleanup
        if downloaded_path.exists():
            downloaded_path.unlink()

    def test_open_nonexistent_file(self, file_service, temp_db):
        """Opening non-existent file returns error."""
        downloaded_path, error = file_service.open_file("nonexistent.pdf", issue_id=1)

        assert downloaded_path is None
        assert "not found" in error.lower()


class TestGetAttachmentFileInfo:
    """Test file info retrieval."""

    def test_get_info_existing_file(self, file_service, temp_db, sample_file):
        """Returns correct info for existing file."""
        filename, _ = file_service.add_file(sample_file, issue_id=1)

        info = file_service.get_attachment_file_info(filename, issue_id=1)

        assert info["exists"] is True
        assert info["size"] > 0
        assert info["display_name"] == filename
        assert info["is_legacy"] is False
        assert info["full_path"] is not None

    def test_get_info_missing_file(self, file_service, temp_db):
        """Returns correct info for missing file."""
        info = file_service.get_attachment_file_info("missing.pdf", issue_id=1)

        assert info["exists"] is False
        assert info["size"] == 0
        assert info["display_name"] == "missing.pdf"
        assert info["full_path"] is None

    def test_get_info_legacy_path(self, file_service, temp_db, sample_file):
        """Detects legacy path format and extracts display name."""
        legacy_path = "C:\\Users\\test\\Documents\\report.pdf"

        info = file_service.get_attachment_file_info(legacy_path, issue_id=1)

        assert info["is_legacy"] is True
        assert info["display_name"] == "report.pdf"


class TestDownloadsFolder:
    """Test Downloads folder detection."""

    def test_get_downloads_folder_exists(self, file_service):
        """Returns a valid Downloads folder path."""
        downloads = file_service.get_downloads_folder()

        assert downloads is not None
        assert downloads.exists()


class TestSingleton:
    """Test singleton pattern."""

    def test_get_file_service_singleton(self, temp_db):
        """get_file_service returns same instance."""
        reset_file_service()
        service1 = get_file_service()
        service2 = get_file_service()

        assert service1 is service2

    def test_reset_file_service(self, temp_db):
        """reset_file_service creates new instance on next call."""
        reset_file_service()
        service1 = get_file_service()
        reset_file_service()
        service2 = get_file_service()

        assert service1 is not service2


class TestFolderCreation:
    """Test automatic folder creation."""

    def test_issue_folder_created_on_add(self, file_service, temp_db, sample_file):
        """Issue folder is created automatically when adding file."""
        issue_folder = file_service.get_issue_folder(99)
        assert not issue_folder.exists()

        file_service.add_file(sample_file, issue_id=99)

        assert issue_folder.exists()

    def test_deleted_folder_created_on_remove(self, file_service, temp_db, sample_file):
        """Deleted folder is created automatically when removing file."""
        filename, _ = file_service.add_file(sample_file, issue_id=1)

        deleted_folder = file_service.get_deleted_folder(1)
        assert not deleted_folder.exists()

        file_service.remove_file(filename, issue_id=1)

        assert deleted_folder.exists()
