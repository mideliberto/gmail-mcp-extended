"""Type stubs for VaultProcessor."""

from pathlib import Path
from typing import Any, Dict, List, Optional, Union

class VaultProcessor:
    vault_path: str

    def __init__(self, vault_path: Optional[str] = None) -> None: ...

    def save_to_vault(
        self,
        content: str,
        filename: str,
        vault_path: Optional[str] = None,
        folder: str = "0-inbox",
        source: str = "local",
        original_path: Optional[str] = None,
        tags: Optional[List[str]] = None,
        frontmatter_extra: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]: ...

    def save_file_to_vault(
        self,
        file_path: Union[str, Path],
        vault_path: Optional[str] = None,
        folder: str = "0-inbox",
        tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]: ...

    def batch_save_to_vault(
        self,
        files: List[Dict[str, Any]],
        vault_path: Optional[str] = None,
        folder: str = "0-inbox",
        tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]: ...

    def doc_to_vault(
        self,
        file_path: Union[str, Path],
        vault_path: Optional[str] = None,
        folder: str = "0-inbox",
        tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]: ...

    def ocr_to_vault(
        self,
        file_path: Union[str, Path],
        vault_path: Optional[str] = None,
        folder: str = "0-inbox",
        language: str = "eng",
        tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]: ...

def get_vault_processor() -> VaultProcessor: ...
