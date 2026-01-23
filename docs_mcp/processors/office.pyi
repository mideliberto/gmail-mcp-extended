"""Type stubs for OfficeProcessor."""

from pathlib import Path
from typing import Any, Dict, List, Optional, Union

class OfficeProcessor:
    def __init__(self) -> None: ...

    # DOCX
    def read_docx(self, file_path: Union[str, Path]) -> Dict[str, Any]: ...
    def fill_docx_template(
        self,
        template_path: Union[str, Path],
        data: Dict[str, Any],
        output_path: Optional[Union[str, Path]] = None,
    ) -> Dict[str, Any]: ...
    def docx_to_markdown(self, file_path: Union[str, Path]) -> Dict[str, Any]: ...

    # XLSX
    def read_xlsx(
        self,
        file_path: Union[str, Path],
        sheet_name: Optional[str] = None,
    ) -> Dict[str, Any]: ...
    def fill_xlsx_template(
        self,
        template_path: Union[str, Path],
        data: Dict[str, Any],
        output_path: Optional[Union[str, Path]] = None,
    ) -> Dict[str, Any]: ...
    def xlsx_to_csv(
        self,
        file_path: Union[str, Path],
        sheet_name: Optional[str] = None,
    ) -> Dict[str, Any]: ...

    # PPTX
    def read_pptx(self, file_path: Union[str, Path]) -> Dict[str, Any]: ...
    def fill_pptx_template(
        self,
        template_path: Union[str, Path],
        data: Dict[str, Any],
        output_path: Optional[Union[str, Path]] = None,
    ) -> Dict[str, Any]: ...
    def pptx_to_markdown(self, file_path: Union[str, Path]) -> Dict[str, Any]: ...

def get_office_processor() -> OfficeProcessor: ...
