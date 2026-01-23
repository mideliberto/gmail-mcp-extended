"""
Document processors for docs-mcp.

This package contains processors for different document types:
- office: DOCX, XLSX, PPTX processing
- pdf: PDF processing
- ocr: Local OCR using Tesseract
- vault: Obsidian vault integration
"""

from docs_mcp.processors.office import OfficeProcessor
from docs_mcp.processors.pdf import PdfProcessor
from docs_mcp.processors.ocr import OcrProcessor
from docs_mcp.processors.vault import VaultProcessor

__all__ = ["OfficeProcessor", "PdfProcessor", "OcrProcessor", "VaultProcessor"]
