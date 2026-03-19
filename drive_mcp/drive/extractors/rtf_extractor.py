"""Extract text content from RTF files."""

from striprtf.striprtf import rtf_to_text


def extract_rtf(content_bytes: bytes) -> str:
    """Extract text from an RTF file.

    Args:
        content_bytes: Raw bytes of the RTF file.

    Returns:
        Extracted text content.
    """
    return rtf_to_text(content_bytes.decode("utf-8"))
