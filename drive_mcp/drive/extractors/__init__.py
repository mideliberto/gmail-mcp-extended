"""
Content extractors for Drive file formats.

Routes MIME types to format-specific extraction functions.
"""

from typing import Dict, Callable

from .docx_extractor import extract_docx
from .pdf_extractor import extract_pdf
from .text_extractor import extract_text
from .rtf_extractor import extract_rtf

# MIME type → extractor function mapping
_EXTRACTORS: Dict[str, Callable[..., str]] = {
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": extract_docx,
    "application/pdf": extract_pdf,
    "text/plain": extract_text,
    "text/csv": extract_text,
    "text/markdown": extract_text,
    "application/json": extract_text,
    "application/rtf": extract_rtf,
}

# Native Google formats that should NOT be downloaded
GOOGLE_NATIVE_TYPES = {
    "application/vnd.google-apps.document": "Google Doc",
    "application/vnd.google-apps.spreadsheet": "Google Sheet",
    "application/vnd.google-apps.presentation": "Google Slides",
}

SUPPORTED_MIME_TYPES = set(_EXTRACTORS.keys())


def get_extractor(mime_type: str) -> Callable[..., str]:
    """Get the extractor function for a MIME type.

    Args:
        mime_type: The MIME type of the file.

    Returns:
        The extractor function.

    Raises:
        ValueError: If the MIME type is not supported.
    """
    if mime_type in GOOGLE_NATIVE_TYPES:
        label = GOOGLE_NATIVE_TYPES[mime_type]
        raise ValueError(
            f"File is a native {label}. "
            "Use docs_mcp read_document for Google Docs, "
            "or export to a supported format first."
        )

    extractor = _EXTRACTORS.get(mime_type)
    if extractor is None:
        supported = ".docx, .pdf, .txt, .csv, .md, .json, .rtf"
        raise ValueError(
            f"Unsupported format: {mime_type}. "
            f"Supported: {supported}. "
            "For Google Docs, use docs_mcp read_document."
        )
    return extractor
