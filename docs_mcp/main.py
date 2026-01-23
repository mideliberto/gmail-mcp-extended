#!/usr/bin/env python3
"""
Docs MCP Server

This module provides the main entry point for the Docs MCP server.
Unlike gmail-mcp and drive-mcp, this server does NOT require Google authentication.
It processes local documents (DOCX, XLSX, PPTX, PDF) and provides OCR capabilities.
"""

import os
import sys
import logging
import traceback

from mcp.server.fastmcp import FastMCP

# Set up basic logging for docs_mcp
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("docs_mcp")

# Create FastMCP application
mcp = FastMCP(
    name=os.getenv("MCP_SERVER_NAME", "Docs MCP"),
)

# Import and setup tools after mcp is created
from docs_mcp.mcp.tools import setup_tools
from docs_mcp.mcp.resources import setup_resources

setup_tools(mcp)
setup_resources(mcp)


def check_dependencies() -> bool:
    """
    Check if required dependencies are available.

    Returns:
        bool: True if all required dependencies are available.
    """
    missing = []

    # Check Python packages
    try:
        import docx
    except ImportError:
        missing.append("python-docx")

    try:
        import openpyxl
    except ImportError:
        missing.append("openpyxl")

    try:
        import pptx
    except ImportError:
        missing.append("python-pptx")

    try:
        import pypdf
    except ImportError:
        missing.append("pypdf")

    try:
        import pdfplumber
    except ImportError:
        missing.append("pdfplumber")

    if missing:
        logger.warning(f"Missing optional dependencies: {', '.join(missing)}")
        logger.warning("Some features may not be available. Install with:")
        logger.warning(f"  pip install {' '.join(missing)}")

    # Check for OCR dependencies (optional)
    try:
        import pytesseract
        # Check if tesseract is actually installed
        pytesseract.get_tesseract_version()
    except Exception:
        logger.info("Tesseract OCR not available. Local OCR features will be disabled.")
        logger.info("Install with: brew install tesseract (macOS) or apt install tesseract-ocr (Linux)")

    return True  # Don't fail startup for missing optional deps


def main() -> None:
    """
    Main entry point for the Docs MCP server.
    """
    try:
        # Check dependencies
        check_dependencies()

        # Run the MCP server
        logger.info("Starting Docs MCP server")
        mcp.run()
    except Exception as e:
        logger.error(f"Error running MCP server: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
