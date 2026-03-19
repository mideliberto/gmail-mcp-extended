"""Extract text content from plain text formats (.txt, .csv, .md, .json)."""


def extract_text(content_bytes: bytes) -> str:
    """Decode raw bytes to text string.

    Tries UTF-8 first, falls back to latin-1.

    Args:
        content_bytes: Raw bytes of the text file.

    Returns:
        Decoded text content.
    """
    try:
        return content_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return content_bytes.decode("latin-1")
