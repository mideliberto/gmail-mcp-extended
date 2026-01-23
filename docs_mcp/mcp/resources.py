"""
MCP Resources for Docs MCP server.

This module provides resource definitions for the Docs MCP server.
"""

import logging
from typing import Any, Dict

from mcp.server.fastmcp import FastMCP

from docs_mcp.processors.ocr import get_ocr_processor

logger = logging.getLogger("docs_mcp.resources")


def setup_resources(mcp: FastMCP) -> None:
    """
    Set up all Docs MCP resources.

    Args:
        mcp: The FastMCP application instance.
    """

    @mcp.resource("status://capabilities")
    def capabilities_status() -> Dict[str, Any]:
        """
        Get the current capabilities status.

        Returns:
            Dict containing available features and their status.
        """
        capabilities = {
            "office": {
                "docx": False,
                "xlsx": False,
                "pptx": False,
            },
            "pdf": {
                "read": False,
                "merge_split": False,
            },
            "ocr": {
                "tesseract": False,
                "pdf2image": False,
            },
        }

        # Check Office dependencies
        try:
            import docx
            capabilities["office"]["docx"] = True
        except ImportError:
            pass

        try:
            import openpyxl
            capabilities["office"]["xlsx"] = True
        except ImportError:
            pass

        try:
            import pptx
            capabilities["office"]["pptx"] = True
        except ImportError:
            pass

        # Check PDF dependencies
        try:
            import pdfplumber
            capabilities["pdf"]["read"] = True
        except ImportError:
            pass

        try:
            import pypdf
            capabilities["pdf"]["merge_split"] = True
        except ImportError:
            pass

        # Check OCR dependencies
        ocr_processor = get_ocr_processor()
        capabilities["ocr"]["tesseract"] = ocr_processor.is_available()

        try:
            from pdf2image import convert_from_path
            capabilities["ocr"]["pdf2image"] = True
        except ImportError:
            pass

        # Determine overall status
        all_office = all(capabilities["office"].values())
        all_pdf = all(capabilities["pdf"].values())
        all_ocr = all(capabilities["ocr"].values())

        return {
            "capabilities": capabilities,
            "summary": {
                "office_ready": all_office,
                "pdf_ready": all_pdf,
                "ocr_ready": all_ocr,
                "fully_ready": all_office and all_pdf and all_ocr,
            },
            "install_hints": {
                "office": "pip install python-docx openpyxl python-pptx",
                "pdf": "pip install pdfplumber pypdf",
                "ocr": "pip install pytesseract pdf2image Pillow && brew install tesseract poppler",
            },
        }

    logger.info("Docs MCP resources registered successfully")
