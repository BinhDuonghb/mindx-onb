"""Unit tests for FileLoader utility."""
import pytest
from pathlib import Path
import sys

# Add the project root to path so we can import from cli
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from cli.utils.file_loader import FileLoader, FileLoadError


class TestFileLoaderLoadFile:
    """Test FileLoader.load_file() method."""

    def test_load_valid_file(self, tmp_path):
        """Should load content from a valid file."""
        test_file = tmp_path / "test.md"
        content = "This is test content."
        test_file.write_text(content, encoding="utf-8")

        result = FileLoader.load_file(str(test_file))

        assert result == content

    def test_load_multiline_file(self, tmp_path):
        """Should load multi-line file content."""
        test_file = tmp_path / "multiline.txt"
        content = "Line 1\nLine 2\nLine 3"
        test_file.write_text(content, encoding="utf-8")

        result = FileLoader.load_file(str(test_file))

        assert result == content

    def test_load_unicode_file(self, tmp_path):
        """Should load file with unicode characters."""
        test_file = tmp_path / "unicode.md"
        content = "Content with émojis 🎉 and spëcial chars!"
        test_file.write_text(content, encoding="utf-8")

        result = FileLoader.load_file(str(test_file))

        assert result == content

    def test_load_markdown_file(self, tmp_path):
        """Should load markdown file."""
        test_file = tmp_path / "template.md"
        content = """# Title

This is a **template** with *formatting*.

- Item 1
- Item 2
"""
        test_file.write_text(content, encoding="utf-8")

        result = FileLoader.load_file(str(test_file))

        assert result == content
        assert "# Title" in result

    def test_error_nonexistent_file(self, tmp_path):
        """Should raise FileLoadError for non-existent file."""
        nonexistent = tmp_path / "nonexistent.txt"

        with pytest.raises(FileLoadError, match="File not found"):
            FileLoader.load_file(str(nonexistent))

    def test_error_empty_file(self, tmp_path):
        """Should raise FileLoadError for empty file."""
        empty_file = tmp_path / "empty.txt"
        empty_file.write_text("", encoding="utf-8")

        with pytest.raises(FileLoadError, match="empty"):
            FileLoader.load_file(str(empty_file))

    def test_error_whitespace_only_file(self, tmp_path):
        """Should raise FileLoadError for file with only whitespace."""
        whitespace_file = tmp_path / "whitespace.txt"
        whitespace_file.write_text("   \n\n  ", encoding="utf-8")

        with pytest.raises(FileLoadError, match="empty"):
            FileLoader.load_file(str(whitespace_file))

    def test_error_directory_instead_of_file(self, tmp_path):
        """Should raise FileLoadError when path is directory."""
        subdir = tmp_path / "subdir"
        subdir.mkdir()

        with pytest.raises(FileLoadError, match="not a file"):
            FileLoader.load_file(str(subdir))

    def test_preserves_leading_whitespace(self, tmp_path):
        """Should preserve leading whitespace in content."""
        test_file = tmp_path / "indent.txt"
        content = "    indented line\n  less indented"
        test_file.write_text(content, encoding="utf-8")

        result = FileLoader.load_file(str(test_file))

        assert result == content
        assert result.startswith("    ")

    def test_load_large_file(self, tmp_path):
        """Should load large files."""
        test_file = tmp_path / "large.txt"
        # Create 1MB file
        content = "x" * (1024 * 1024)
        test_file.write_text(content, encoding="utf-8")

        result = FileLoader.load_file(str(test_file))

        assert len(result) == 1024 * 1024
        assert result == content
