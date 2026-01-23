"""
Tests for Docs MCP processors.
"""

import os
import tempfile
import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch


class TestOfficeProcessor:
    """Tests for Office document processing."""

    def test_read_docx_missing_file(self):
        """Test reading a non-existent DOCX file."""
        from docs_mcp.processors.office import get_office_processor
        processor = get_office_processor()

        result = processor.read_docx("/nonexistent/file.docx")

        assert "error" in result

    def test_read_xlsx_missing_file(self):
        """Test reading a non-existent XLSX file."""
        from docs_mcp.processors.office import get_office_processor
        processor = get_office_processor()

        result = processor.read_xlsx("/nonexistent/file.xlsx")

        assert "error" in result

    def test_read_pptx_missing_file(self):
        """Test reading a non-existent PPTX file."""
        from docs_mcp.processors.office import get_office_processor
        processor = get_office_processor()

        result = processor.read_pptx("/nonexistent/file.pptx")

        assert "error" in result

    def test_read_docx_invalid_file(self):
        """Test reading an invalid DOCX file."""
        from docs_mcp.processors.office import get_office_processor
        processor = get_office_processor()

        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
            f.write(b"this is not a valid docx file")
            temp_path = f.name

        try:
            result = processor.read_docx(temp_path)
            # Should return an error for invalid file
            assert "error" in result
        finally:
            os.unlink(temp_path)

    def test_read_xlsx_invalid_file(self):
        """Test reading an invalid XLSX file."""
        from docs_mcp.processors.office import get_office_processor
        processor = get_office_processor()

        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            f.write(b"this is not a valid xlsx file")
            temp_path = f.name

        try:
            result = processor.read_xlsx(temp_path)
            # Should return an error for invalid file
            assert "error" in result
        finally:
            os.unlink(temp_path)


class TestPdfProcessor:
    """Tests for PDF processing."""

    def test_read_pdf_missing_file(self):
        """Test reading a non-existent PDF file."""
        from docs_mcp.processors.pdf import get_pdf_processor
        processor = get_pdf_processor()

        result = processor.read_pdf("/nonexistent/file.pdf")

        assert "error" in result

    def test_get_metadata_missing_file(self):
        """Test getting metadata from non-existent PDF."""
        from docs_mcp.processors.pdf import get_pdf_processor
        processor = get_pdf_processor()

        result = processor.get_pdf_metadata("/nonexistent/file.pdf")

        assert "error" in result

    def test_merge_pdfs_missing_files(self):
        """Test merging with non-existent files."""
        from docs_mcp.processors.pdf import get_pdf_processor
        processor = get_pdf_processor()

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = os.path.join(temp_dir, "output.pdf")
            result = processor.merge_pdfs(["/nonexistent/file1.pdf"], output_path)

            # Should error for missing file
            assert "error" in result

    def test_split_pdf_missing_file(self):
        """Test splitting a non-existent PDF."""
        from docs_mcp.processors.pdf import get_pdf_processor
        processor = get_pdf_processor()

        result = processor.split_pdf("/nonexistent/file.pdf", "/tmp/output")

        assert "error" in result


class TestOcrProcessor:
    """Tests for OCR processing."""

    def test_is_available(self):
        """Test checking if Tesseract is available."""
        from docs_mcp.processors.ocr import get_ocr_processor
        processor = get_ocr_processor()

        # Should return a boolean
        result = processor.is_available()
        assert isinstance(result, bool)

    def test_ocr_image_missing_file(self):
        """Test OCR on non-existent image."""
        from docs_mcp.processors.ocr import get_ocr_processor
        processor = get_ocr_processor()

        result = processor.ocr_image("/nonexistent/image.png")

        assert "error" in result

    def test_ocr_pdf_missing_file(self):
        """Test OCR on non-existent PDF."""
        from docs_mcp.processors.ocr import get_ocr_processor
        processor = get_ocr_processor()

        result = processor.ocr_pdf("/nonexistent/file.pdf")

        assert "error" in result

    def test_ocr_file_unsupported_type(self):
        """Test OCR on unsupported file type."""
        from docs_mcp.processors.ocr import get_ocr_processor
        processor = get_ocr_processor()

        with tempfile.NamedTemporaryFile(suffix=".xyz", delete=False) as f:
            f.write(b"fake content")
            temp_path = f.name

        try:
            result = processor.ocr_file(temp_path)
            assert "error" in result
        finally:
            os.unlink(temp_path)


class TestVaultProcessor:
    """Tests for Vault integration."""

    def test_vault_path_not_configured(self):
        """Test error when vault path not configured."""
        from docs_mcp.processors.vault import VaultProcessor
        processor = VaultProcessor(vault_path="")

        result = processor.save_to_vault("content", "filename")

        assert "error" in result

    def test_save_to_vault_success(self):
        """Test saving content to vault."""
        from docs_mcp.processors.vault import VaultProcessor

        with tempfile.TemporaryDirectory() as temp_dir:
            processor = VaultProcessor(vault_path=temp_dir)

            result = processor.save_to_vault(
                content="# Test Content\n\nThis is a test.",
                filename="test-note",
                folder="inbox",
            )

            assert result.get("success") is True
            assert "file_path" in result

            # Verify file was created
            file_path = Path(result["file_path"])
            assert file_path.exists()

            # Verify content
            content = file_path.read_text()
            assert "Test Content" in content
            assert "---" in content  # Frontmatter

    def test_save_file_to_vault_missing_source(self):
        """Test saving non-existent file to vault."""
        from docs_mcp.processors.vault import VaultProcessor

        with tempfile.TemporaryDirectory() as temp_dir:
            processor = VaultProcessor(vault_path=temp_dir)

            result = processor.save_file_to_vault("/nonexistent/file.txt")

            assert "error" in result

    def test_batch_save_to_vault(self):
        """Test batch saving to vault."""
        from docs_mcp.processors.vault import VaultProcessor

        with tempfile.TemporaryDirectory() as temp_dir:
            processor = VaultProcessor(vault_path=temp_dir)

            files = [
                {"content": "Content 1", "filename": "note1"},
                {"content": "Content 2", "filename": "note2"},
            ]

            result = processor.batch_save_to_vault(files)

            assert result["saved"] == 2
            assert result["failed"] == 0

    def test_sanitize_filename(self):
        """Test filename sanitization."""
        from docs_mcp.processors.vault import VaultProcessor
        processor = VaultProcessor()

        # Test various problematic characters
        assert processor._sanitize_filename("file/with\\slashes") == "file-with-slashes"
        assert processor._sanitize_filename("file:with:colons") == "file-with-colons"
        assert processor._sanitize_filename("file<with>brackets") == "file-with-brackets"
        assert processor._sanitize_filename('file"with"quotes') == "file-with-quotes"

    def test_create_frontmatter(self):
        """Test frontmatter creation."""
        from docs_mcp.processors.vault import VaultProcessor
        processor = VaultProcessor()

        frontmatter = processor._create_frontmatter(
            source="test",
            original_path="/path/to/file.pdf",
            tags=["tag1", "tag2"],
        )

        assert "---" in frontmatter
        assert "type: doc-import" in frontmatter
        assert "source: test" in frontmatter
        assert "tag1" in frontmatter
        assert "tag2" in frontmatter


class TestDocsMcpTools:
    """Tests for docs-mcp tool registration."""

    def test_tools_registered(self):
        """Test that all tools are registered."""
        from docs_mcp.main import mcp

        tools = list(mcp._tool_manager._tools.keys())

        # Verify expected tools exist
        expected_tools = [
            "read_docx_content",
            "read_xlsx_content",
            "read_pptx_content",
            "fill_docx_template",
            "docx_to_markdown",
            "read_pdf_content",
            "merge_pdfs",
            "ocr_image_local",
            "save_text_to_vault",
        ]

        for tool in expected_tools:
            assert tool in tools, f"Missing tool: {tool}"

    def test_tool_count(self):
        """Test that we have the expected number of tools."""
        from docs_mcp.main import mcp

        tools = list(mcp._tool_manager._tools.keys())
        assert len(tools) == 27, f"Expected 27 tools, got {len(tools)}"
