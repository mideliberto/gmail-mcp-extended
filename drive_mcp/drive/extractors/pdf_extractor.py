"""Extract text content from PDF files."""

import fitz  # PyMuPDF


def extract_pdf(content_bytes: bytes) -> str:
    """Extract text from a PDF file, page by page.

    Args:
        content_bytes: Raw bytes of the PDF file.

    Returns:
        Extracted text content with page markers.
    """
    doc = fitz.open(stream=content_bytes, filetype="pdf")
    parts = []
    for page in doc:
        text = page.get_text()
        if text.strip():
            parts.append(f"--- Page {page.number + 1} ---\n{text}")
    doc.close()
    return "\n\n".join(parts)
