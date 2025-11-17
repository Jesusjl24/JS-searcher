"""
Unit tests for file handlers
"""

import pytest
import io
from src.file_handlers import (
    validate_file,
    extract_text_from_txt,
    get_file_info,
    UnsupportedFileTypeError,
    FileSizeExceededError,
)


class MockUploadedFile:
    """Mock Streamlit UploadedFile for testing"""

    def __init__(self, name, content, size=None):
        self.name = name
        self.content = content.encode('utf-8') if isinstance(content, str) else content
        self.size = size if size is not None else len(self.content)
        self._position = 0

    def read(self):
        return self.content

    def seek(self, position):
        self._position = position


class TestValidation:
    """Test file validation"""

    def test_validate_file_valid_pdf(self):
        file = MockUploadedFile("resume.pdf", "test content")
        # Should not raise
        validate_file(file)

    def test_validate_file_valid_docx(self):
        file = MockUploadedFile("resume.docx", "test content")
        validate_file(file)

    def test_validate_file_valid_txt(self):
        file = MockUploadedFile("resume.txt", "test content")
        validate_file(file)

    def test_validate_file_invalid_extension(self):
        file = MockUploadedFile("resume.exe", "malicious content")
        with pytest.raises(UnsupportedFileTypeError):
            validate_file(file)

    def test_validate_file_too_large(self):
        large_content = "x" * (11 * 1024 * 1024)  # 11MB
        file = MockUploadedFile("resume.pdf", large_content)
        with pytest.raises(FileSizeExceededError):
            validate_file(file)


class TestTextExtraction:
    """Test text extraction from different file types"""

    def test_extract_text_from_txt_simple(self):
        content = "This is a test resume\nWith multiple lines"
        file = MockUploadedFile("resume.txt", content)
        extracted = extract_text_from_txt(file)
        assert extracted == content

    def test_extract_text_from_txt_empty_raises(self):
        file = MockUploadedFile("resume.txt", "")
        with pytest.raises(Exception):  # Should raise FileReadError
            extract_text_from_txt(file)


class TestFileInfo:
    """Test file info extraction"""

    def test_get_file_info_pdf(self):
        file = MockUploadedFile("test.pdf", "content")
        info = get_file_info(file)

        assert info["name"] == "test.pdf"
        assert info["extension"] == "PDF"
        assert info["is_valid"] is True
        assert info["within_size_limit"] is True

    def test_get_file_info_invalid_type(self):
        file = MockUploadedFile("test.exe", "content")
        info = get_file_info(file)

        assert info["is_valid"] is False

    def test_get_file_info_sizes(self):
        content = "x" * 1024  # 1KB
        file = MockUploadedFile("test.txt", content)
        info = get_file_info(file)

        assert info["size_bytes"] == 1024
        assert info["size_kb"] == 1.0
        assert info["size_mb"] < 0.01


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
