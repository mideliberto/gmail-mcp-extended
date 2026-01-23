"""
MCP Tools for Docs MCP server.

This module provides all the tool definitions for the Docs MCP server.
"""

import base64
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP

from docs_mcp.processors.office import get_office_processor
from docs_mcp.processors.pdf import get_pdf_processor
from docs_mcp.processors.ocr import get_ocr_processor
from docs_mcp.processors.vault import get_vault_processor

logger = logging.getLogger("docs_mcp.tools")


def setup_tools(mcp: FastMCP) -> None:
    """
    Set up all Docs MCP tools.

    Args:
        mcp: The FastMCP application instance.
    """

    # =========================================================================
    # Office Document Reading (3 tools)
    # =========================================================================

    @mcp.tool()
    def read_docx_content(file_path: str) -> Dict[str, Any]:
        """
        Extract text, tables, and structure from a DOCX file.

        Args:
            file_path: Absolute path to the DOCX file.

        Returns:
            Dict containing:
                - text: Full extracted text
                - paragraphs: List of paragraphs with style info
                - tables: List of tables as 2D arrays
                - metadata: Document metadata (author, title, dates)
        """
        processor = get_office_processor()
        return processor.read_docx(file_path)

    @mcp.tool()
    def read_xlsx_content(
        file_path: str,
        sheet_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Read spreadsheet data from an XLSX file.

        Args:
            file_path: Absolute path to the XLSX file.
            sheet_name: Specific sheet to read. If not provided, reads all sheets.

        Returns:
            Dict containing:
                - sheets: Dict of sheet names to data
                - sheet_names: List of all sheet names
                - active_sheet: Name of the active sheet
        """
        processor = get_office_processor()
        return processor.read_xlsx(file_path, sheet_name)

    @mcp.tool()
    def read_pptx_content(file_path: str) -> Dict[str, Any]:
        """
        Extract slides, text, and speaker notes from a PPTX file.

        Args:
            file_path: Absolute path to the PPTX file.

        Returns:
            Dict containing:
                - slides: List of slides with title, content, and notes
                - slide_count: Number of slides
        """
        processor = get_office_processor()
        return processor.read_pptx(file_path)

    # =========================================================================
    # Office Template Processing (6 tools)
    # =========================================================================

    @mcp.tool()
    def fill_docx_template(
        template_path: str,
        data: Dict[str, str],
        output_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Replace {{placeholders}} in a DOCX template with data values.

        Args:
            template_path: Path to the template DOCX file.
            data: Dict mapping placeholder names to replacement values.
            output_path: Where to save the result. If not provided, returns base64 content.

        Returns:
            Dict with success status and output path or base64 content.
        """
        processor = get_office_processor()
        result = processor.fill_docx_template(template_path, data, output_path)

        if "content" in result and isinstance(result["content"], bytes):
            result["content"] = base64.b64encode(result["content"]).decode("ascii")
            result["encoding"] = "base64"

        return result

    @mcp.tool()
    def fill_xlsx_template(
        template_path: str,
        data: Dict[str, str],
        output_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Replace {{placeholders}} in an XLSX template with data values.

        Args:
            template_path: Path to the template XLSX file.
            data: Dict mapping placeholder names to replacement values.
            output_path: Where to save the result.

        Returns:
            Dict with success status and output path or base64 content.
        """
        processor = get_office_processor()
        result = processor.fill_xlsx_template(template_path, data, output_path)

        if "content" in result and isinstance(result["content"], bytes):
            result["content"] = base64.b64encode(result["content"]).decode("ascii")
            result["encoding"] = "base64"

        return result

    @mcp.tool()
    def fill_pptx_template(
        template_path: str,
        data: Dict[str, str],
        output_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Replace {{placeholders}} in a PPTX template with data values.

        Args:
            template_path: Path to the template PPTX file.
            data: Dict mapping placeholder names to replacement values.
            output_path: Where to save the result.

        Returns:
            Dict with success status and output path or base64 content.
        """
        processor = get_office_processor()
        result = processor.fill_pptx_template(template_path, data, output_path)

        if "content" in result and isinstance(result["content"], bytes):
            result["content"] = base64.b64encode(result["content"]).decode("ascii")
            result["encoding"] = "base64"

        return result

    @mcp.tool()
    def create_docx_from_template(
        template_path: str,
        data: Dict[str, str],
        output_path: str,
    ) -> Dict[str, Any]:
        """
        Generate a new DOCX from a template with data.

        Alias for fill_docx_template with required output_path.

        Args:
            template_path: Path to the template DOCX file.
            data: Dict mapping placeholder names to replacement values.
            output_path: Where to save the generated file.

        Returns:
            Dict with success status and output path.
        """
        processor = get_office_processor()
        return processor.fill_docx_template(template_path, data, output_path)

    @mcp.tool()
    def create_xlsx_from_template(
        template_path: str,
        data: Dict[str, str],
        output_path: str,
    ) -> Dict[str, Any]:
        """
        Generate a new XLSX from a template with data.

        Args:
            template_path: Path to the template XLSX file.
            data: Dict mapping placeholder names to replacement values.
            output_path: Where to save the generated file.

        Returns:
            Dict with success status and output path.
        """
        processor = get_office_processor()
        return processor.fill_xlsx_template(template_path, data, output_path)

    @mcp.tool()
    def create_pptx_from_template(
        template_path: str,
        data: Dict[str, str],
        output_path: str,
    ) -> Dict[str, Any]:
        """
        Generate a new PPTX from a template with data.

        Args:
            template_path: Path to the template PPTX file.
            data: Dict mapping placeholder names to replacement values.
            output_path: Where to save the generated file.

        Returns:
            Dict with success status and output path.
        """
        processor = get_office_processor()
        return processor.fill_pptx_template(template_path, data, output_path)

    # =========================================================================
    # Office Export (3 tools)
    # =========================================================================

    @mcp.tool()
    def docx_to_markdown(file_path: str) -> Dict[str, Any]:
        """
        Convert a DOCX file to Markdown format.

        Args:
            file_path: Path to the DOCX file.

        Returns:
            Dict containing:
                - markdown: The converted markdown text
                - metadata: Document metadata
        """
        processor = get_office_processor()
        return processor.docx_to_markdown(file_path)

    @mcp.tool()
    def xlsx_to_csv(
        file_path: str,
        sheet_name: Optional[str] = None,
        delimiter: str = ",",
    ) -> Dict[str, Any]:
        """
        Export an XLSX sheet to CSV format.

        Args:
            file_path: Path to the XLSX file.
            sheet_name: Sheet to export. Uses first sheet if not specified.
            delimiter: CSV delimiter character (default: comma).

        Returns:
            Dict containing:
                - csv: The CSV text
                - sheet_name: Name of the exported sheet
                - rows: Number of rows
        """
        processor = get_office_processor()
        return processor.xlsx_to_csv(file_path, sheet_name, delimiter)

    @mcp.tool()
    def pptx_to_markdown(file_path: str) -> Dict[str, Any]:
        """
        Extract PPTX content as a Markdown outline.

        Args:
            file_path: Path to the PPTX file.

        Returns:
            Dict containing:
                - markdown: The markdown outline
                - slide_count: Number of slides
        """
        processor = get_office_processor()
        return processor.pptx_to_markdown(file_path)

    # =========================================================================
    # PDF Processing (7 tools)
    # =========================================================================

    @mcp.tool()
    def read_pdf_content(file_path: str) -> Dict[str, Any]:
        """
        Extract text from a PDF file.

        Works best with native text PDFs. For scanned PDFs, use ocr_pdf_local.

        Args:
            file_path: Path to the PDF file.

        Returns:
            Dict containing:
                - text: Full extracted text
                - pages: List of pages with text and dimensions
                - page_count: Number of pages
        """
        processor = get_pdf_processor()
        return processor.read_pdf(file_path)

    @mcp.tool()
    def get_pdf_metadata(file_path: str) -> Dict[str, Any]:
        """
        Get PDF properties and metadata.

        Args:
            file_path: Path to the PDF file.

        Returns:
            Dict containing title, author, subject, creator, dates, page count, encryption status.
        """
        processor = get_pdf_processor()
        return processor.get_pdf_metadata(file_path)

    @mcp.tool()
    def pdf_to_markdown(file_path: str) -> Dict[str, Any]:
        """
        Convert a PDF to Markdown format.

        Args:
            file_path: Path to the PDF file.

        Returns:
            Dict containing:
                - markdown: The converted markdown with frontmatter
                - page_count: Number of pages
                - metadata: PDF metadata
        """
        processor = get_pdf_processor()
        return processor.pdf_to_markdown(file_path)

    @mcp.tool()
    def extract_pdf_images(
        file_path: str,
        output_dir: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Extract embedded images from a PDF.

        Args:
            file_path: Path to the PDF file.
            output_dir: Directory to save extracted images. If not provided, only lists images.

        Returns:
            Dict containing:
                - images: List of image info (page, dimensions, format)
                - image_count: Number of images found
        """
        processor = get_pdf_processor()
        return processor.extract_pdf_images(file_path, output_dir)

    @mcp.tool()
    def merge_pdfs(
        pdf_paths: List[str],
        output_path: str,
    ) -> Dict[str, Any]:
        """
        Combine multiple PDFs into one.

        Args:
            pdf_paths: List of paths to PDF files to merge (in order).
            output_path: Where to save the merged PDF.

        Returns:
            Dict containing:
                - success: Whether merge succeeded
                - output_path: Path to merged PDF
                - total_pages: Total pages in merged PDF
                - files_merged: Number of files merged
        """
        processor = get_pdf_processor()
        return processor.merge_pdfs(pdf_paths, output_path)

    @mcp.tool()
    def split_pdf(
        file_path: str,
        output_dir: str,
        pages: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Split a PDF into separate pages or page ranges.

        Args:
            file_path: Path to the PDF file.
            output_dir: Directory to save split PDFs.
            pages: Page specification (e.g., "1-3,5,7-9"). If not provided, splits into individual pages.

        Returns:
            Dict containing:
                - success: Whether split succeeded
                - output_files: List of created file paths
                - files_created: Number of files created
        """
        processor = get_pdf_processor()
        return processor.split_pdf(file_path, output_dir, pages)

    @mcp.tool()
    def fill_pdf_form(
        file_path: str,
        data: Dict[str, str],
        output_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Fill PDF form fields.

        Only works with PDFs that have fillable form fields.

        Args:
            file_path: Path to the PDF form.
            data: Dict mapping field names to values.
            output_path: Where to save the filled PDF.

        Returns:
            Dict with success status and output path or base64 content.
        """
        processor = get_pdf_processor()
        result = processor.fill_pdf_form(file_path, data, output_path)

        if "content" in result and isinstance(result["content"], bytes):
            result["content"] = base64.b64encode(result["content"]).decode("ascii")
            result["encoding"] = "base64"

        return result

    # =========================================================================
    # Local OCR - Tesseract (4 tools)
    # =========================================================================

    @mcp.tool()
    def ocr_image_local(
        file_path: str,
        language: str = "eng",
    ) -> Dict[str, Any]:
        """
        OCR an image file locally using Tesseract.

        Requires Tesseract to be installed:
        - macOS: brew install tesseract
        - Linux: apt install tesseract-ocr

        Args:
            file_path: Path to the image file (PNG, JPG, TIFF, etc.).
            language: Tesseract language code (default: "eng"). Common codes:
                      eng=English, spa=Spanish, fra=French, deu=German, chi_sim=Chinese Simplified

        Returns:
            Dict containing:
                - text: Extracted text
                - confidence: OCR confidence percentage
                - method: "tesseract"
                - word_count: Number of words extracted
        """
        processor = get_ocr_processor()
        return processor.ocr_image(file_path, language)

    @mcp.tool()
    def ocr_pdf_local(
        file_path: str,
        language: str = "eng",
        dpi: int = 300,
        first_page: Optional[int] = None,
        last_page: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        OCR a scanned PDF locally using Tesseract.

        Converts PDF pages to images, then OCRs each page.
        Requires Tesseract and poppler to be installed.

        Args:
            file_path: Path to the PDF file.
            language: Tesseract language code (default: "eng").
            dpi: Resolution for PDF to image conversion (default: 300).
            first_page: First page to OCR (1-indexed, optional).
            last_page: Last page to OCR (optional).

        Returns:
            Dict containing:
                - text: Full extracted text
                - pages: List of pages with individual text and confidence
                - page_count: Number of pages processed
                - confidence: Average confidence percentage
        """
        processor = get_ocr_processor()
        return processor.ocr_pdf(file_path, language, dpi, first_page, last_page)

    @mcp.tool()
    def ocr_file(
        file_path: str,
        language: str = "eng",
    ) -> Dict[str, Any]:
        """
        Smart OCR that auto-detects file type (image or PDF).

        Args:
            file_path: Path to image or PDF file.
            language: Tesseract language code (default: "eng").

        Returns:
            Dict containing OCR results appropriate for the file type.
        """
        processor = get_ocr_processor()
        return processor.ocr_file(file_path, language)

    @mcp.tool()
    def ocr_to_vault(
        file_path: str,
        vault_path: Optional[str] = None,
        folder: str = "0-inbox",
        language: str = "eng",
        tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        OCR an image or PDF and save the text to an Obsidian vault.

        Args:
            file_path: Path to the image or PDF file.
            vault_path: Path to the Obsidian vault (uses VAULT_PATH env var if not provided).
            folder: Folder within vault (default: "0-inbox").
            language: Tesseract language code (default: "eng").
            tags: Additional tags for the note.

        Returns:
            Dict with success status and vault file path.
        """
        processor = get_vault_processor()
        return processor.ocr_to_vault(file_path, vault_path, folder, language, tags)

    # =========================================================================
    # Vault Integration (4 tools)
    # =========================================================================

    @mcp.tool()
    def save_file_to_vault(
        file_path: str,
        vault_path: Optional[str] = None,
        folder: str = "0-inbox",
        tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Save any file to an Obsidian vault.

        Copies the file to the vault directory.

        Args:
            file_path: Path to the file to save.
            vault_path: Path to the Obsidian vault (uses VAULT_PATH env var if not provided).
            folder: Folder within vault (default: "0-inbox").
            tags: Tags for sidecar metadata.

        Returns:
            Dict with success status and vault file path.
        """
        processor = get_vault_processor()
        return processor.save_file_to_vault(file_path, vault_path, folder, tags)

    @mcp.tool()
    def batch_save_to_vault(
        files: List[Dict[str, str]],
        vault_path: Optional[str] = None,
        folder: str = "0-inbox",
        tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Save multiple files to an Obsidian vault.

        Args:
            files: List of dicts with 'content' (markdown) and 'filename' keys.
            vault_path: Path to the Obsidian vault.
            folder: Folder within vault (default: "0-inbox").
            tags: Tags to apply to all files.

        Returns:
            Dict with counts and results for each file.
        """
        processor = get_vault_processor()
        return processor.batch_save_to_vault(files, vault_path, folder, tags)

    @mcp.tool()
    def doc_to_vault(
        file_path: str,
        vault_path: Optional[str] = None,
        folder: str = "0-inbox",
        tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Convert a document to markdown and save to vault.

        Supports DOCX, XLSX, PPTX, and PDF files.

        Args:
            file_path: Path to the document file.
            vault_path: Path to the Obsidian vault.
            folder: Folder within vault (default: "0-inbox").
            tags: Additional tags.

        Returns:
            Dict with success status and vault file path.
        """
        processor = get_vault_processor()
        return processor.doc_to_vault(file_path, vault_path, folder, tags)

    @mcp.tool()
    def save_text_to_vault(
        content: str,
        filename: str,
        vault_path: Optional[str] = None,
        folder: str = "0-inbox",
        tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Save markdown text to an Obsidian vault.

        Args:
            content: The markdown content to save.
            filename: Name for the file (without .md extension).
            vault_path: Path to the Obsidian vault.
            folder: Folder within vault (default: "0-inbox").
            tags: Additional tags.

        Returns:
            Dict with success status and vault file path.
        """
        processor = get_vault_processor()
        return processor.save_to_vault(
            content=content,
            filename=filename,
            vault_path=vault_path,
            folder=folder,
            tags=tags,
        )

    logger.info("Docs MCP tools registered successfully")
