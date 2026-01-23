"""
OCR Processor

Handles local OCR using Tesseract.
"""

import io
import logging
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger("docs_mcp.processors.ocr")


class OcrProcessor:
    """
    Processor for local OCR using Tesseract.
    """

    def __init__(self):
        """Initialize the OCR processor."""
        self._tesseract_available: Optional[bool] = None

    def is_available(self) -> bool:
        """Check if Tesseract is available."""
        if self._tesseract_available is None:
            try:
                import pytesseract
                pytesseract.get_tesseract_version()
                self._tesseract_available = True
            except Exception:
                self._tesseract_available = False
        return self._tesseract_available

    def ocr_image(
        self,
        image_path: Union[str, Path, bytes],
        language: str = "eng",
        config: str = "",
    ) -> Dict[str, Any]:
        """
        OCR an image file using Tesseract.

        Args:
            image_path: Path to the image file or bytes content.
            language: Tesseract language code (default: "eng").
            config: Additional Tesseract config options.

        Returns:
            Dict containing OCR text and confidence.
        """
        if not self.is_available():
            return {
                "error": "Tesseract OCR not available",
                "message": "Install with: brew install tesseract (macOS) or apt install tesseract-ocr (Linux)",
            }

        try:
            import pytesseract
            from PIL import Image
        except ImportError as e:
            return {"error": f"Missing dependency: {e}. Run: pip install pytesseract Pillow"}

        try:
            # Load image
            if isinstance(image_path, bytes):
                image = Image.open(io.BytesIO(image_path))
            else:
                image = Image.open(image_path)

            # Perform OCR
            text = pytesseract.image_to_string(image, lang=language, config=config)

            # Get detailed data for confidence
            data = pytesseract.image_to_data(image, lang=language, output_type=pytesseract.Output.DICT)

            # Calculate average confidence (excluding -1 values which indicate no text)
            confidences = [c for c in data["conf"] if c != -1]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0

            return {
                "text": text.strip(),
                "confidence": round(avg_confidence, 2),
                "method": "tesseract",
                "language": language,
                "word_count": len(text.split()),
            }

        except Exception as e:
            logger.error(f"Error performing OCR on image: {e}")
            return {"error": str(e)}

    def ocr_pdf(
        self,
        pdf_path: Union[str, Path, bytes],
        language: str = "eng",
        dpi: int = 300,
        first_page: Optional[int] = None,
        last_page: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        OCR a scanned PDF using Tesseract.

        Converts PDF pages to images, then OCRs each page.

        Args:
            pdf_path: Path to the PDF file or bytes content.
            language: Tesseract language code.
            dpi: Resolution for PDF to image conversion.
            first_page: First page to OCR (1-indexed, optional).
            last_page: Last page to OCR (optional).

        Returns:
            Dict containing OCR text for each page.
        """
        if not self.is_available():
            return {
                "error": "Tesseract OCR not available",
                "message": "Install with: brew install tesseract (macOS) or apt install tesseract-ocr (Linux)",
            }

        try:
            from pdf2image import convert_from_path, convert_from_bytes
            import pytesseract
        except ImportError as e:
            return {
                "error": f"Missing dependency: {e}",
                "message": "Run: pip install pdf2image pytesseract. Also install poppler: brew install poppler (macOS) or apt install poppler-utils (Linux)",
            }

        try:
            # Convert PDF to images
            convert_kwargs = {"dpi": dpi}
            if first_page:
                convert_kwargs["first_page"] = first_page
            if last_page:
                convert_kwargs["last_page"] = last_page

            if isinstance(pdf_path, bytes):
                images = convert_from_bytes(pdf_path, **convert_kwargs)
            else:
                images = convert_from_path(pdf_path, **convert_kwargs)

            pages = []
            full_text = []
            total_confidence = 0

            for i, image in enumerate(images, start=first_page or 1):
                text = pytesseract.image_to_string(image, lang=language)
                data = pytesseract.image_to_data(image, lang=language, output_type=pytesseract.Output.DICT)

                confidences = [c for c in data["conf"] if c != -1]
                page_confidence = sum(confidences) / len(confidences) if confidences else 0

                pages.append({
                    "number": i,
                    "text": text.strip(),
                    "confidence": round(page_confidence, 2),
                })
                full_text.append(text)
                total_confidence += page_confidence

            avg_confidence = total_confidence / len(pages) if pages else 0

            return {
                "text": "\n\n".join(full_text).strip(),
                "pages": pages,
                "page_count": len(pages),
                "confidence": round(avg_confidence, 2),
                "method": "tesseract",
                "language": language,
            }

        except Exception as e:
            logger.error(f"Error performing OCR on PDF: {e}")
            return {"error": str(e)}

    def ocr_file(
        self,
        file_path: Union[str, Path, bytes],
        language: str = "eng",
    ) -> Dict[str, Any]:
        """
        Smart OCR that auto-detects file type.

        Args:
            file_path: Path to image or PDF file, or bytes content.
            language: Tesseract language code.

        Returns:
            Dict containing OCR results.
        """
        if isinstance(file_path, bytes):
            # Try to detect type from magic bytes
            if file_path[:4] == b"%PDF":
                return self.ocr_pdf(file_path, language=language)
            else:
                # Assume image
                return self.ocr_image(file_path, language=language)
        else:
            path = Path(file_path)
            ext = path.suffix.lower()

            if ext == ".pdf":
                return self.ocr_pdf(file_path, language=language)
            elif ext in [".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp", ".gif", ".webp"]:
                return self.ocr_image(file_path, language=language)
            else:
                return {"error": f"Unsupported file type: {ext}"}


# Singleton instance
_processor: Optional[OcrProcessor] = None


def get_ocr_processor() -> OcrProcessor:
    """Get the singleton OcrProcessor instance."""
    global _processor
    if _processor is None:
        _processor = OcrProcessor()
    return _processor
