"""Type stubs for PdfProcessor."""

from pathlib import Path
from typing import Any, Dict, List, Optional, Union

class PdfProcessor:
    def __init__(self) -> None: ...

    def read_pdf(
        self,
        file_path: Union[str, Path],
        pages: Optional[List[int]] = None,
    ) -> Dict[str, Any]: ...

    def get_metadata(self, file_path: Union[str, Path]) -> Dict[str, Any]: ...

    def pdf_to_markdown(
        self,
        file_path: Union[str, Path],
        pages: Optional[List[int]] = None,
    ) -> Dict[str, Any]: ...

    def extract_images(
        self,
        file_path: Union[str, Path],
        output_dir: Optional[Union[str, Path]] = None,
    ) -> Dict[str, Any]: ...

    def merge_pdfs(
        self,
        file_paths: List[Union[str, Path]],
        output_path: Union[str, Path],
    ) -> Dict[str, Any]: ...

    def split_pdf(
        self,
        file_path: Union[str, Path],
        output_dir: Union[str, Path],
        pages: Optional[List[int]] = None,
    ) -> Dict[str, Any]: ...

    def fill_form(
        self,
        file_path: Union[str, Path],
        data: Dict[str, Any],
        output_path: Optional[Union[str, Path]] = None,
    ) -> Dict[str, Any]: ...

def get_pdf_processor() -> PdfProcessor: ...
