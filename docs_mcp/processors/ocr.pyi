"""Type stubs for OcrProcessor."""

from pathlib import Path
from typing import Any, Dict, Optional, Union

class OcrProcessor:
    def __init__(self) -> None: ...
    def is_available(self) -> bool: ...

    def ocr_image(
        self,
        image_path: Union[str, Path, bytes],
        language: str = "eng",
        config: str = "",
    ) -> Dict[str, Any]: ...

    def ocr_pdf(
        self,
        pdf_path: Union[str, Path, bytes],
        language: str = "eng",
        dpi: int = 300,
        first_page: Optional[int] = None,
        last_page: Optional[int] = None,
    ) -> Dict[str, Any]: ...

    def ocr_file(
        self,
        file_path: Union[str, Path, bytes],
        language: str = "eng",
    ) -> Dict[str, Any]: ...

def get_ocr_processor() -> OcrProcessor: ...
