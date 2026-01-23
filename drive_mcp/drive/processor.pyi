"""Type stubs for DriveProcessor."""

from typing import Any, Dict, List, Optional, Union

class DriveProcessor:
    def __init__(self) -> None: ...
    def _get_service(self) -> Any: ...
    def _get_activity_service(self) -> Any: ...
    def _get_labels_service(self) -> Any: ...

    # File Operations
    def list_files(
        self,
        folder_id: Optional[str] = None,
        page_size: int = 100,
        page_token: Optional[str] = None,
        order_by: str = "modifiedTime desc",
    ) -> Dict[str, Any]: ...

    def search_files(
        self,
        query: str,
        page_size: int = 100,
        page_token: Optional[str] = None,
    ) -> Dict[str, Any]: ...

    def get_file(self, file_id: str) -> Dict[str, Any]: ...
    def read_file(self, file_id: str) -> Dict[str, Any]: ...
    def create_file(
        self,
        name: str,
        content: Union[str, bytes],
        mime_type: str = "text/plain",
        parent_id: Optional[str] = None,
    ) -> Dict[str, Any]: ...

    def update_file(
        self,
        file_id: str,
        content: Union[str, bytes],
        mime_type: Optional[str] = None,
    ) -> Dict[str, Any]: ...

    def rename_file(self, file_id: str, new_name: str) -> Dict[str, Any]: ...
    def move_file(self, file_id: str, new_parent_id: str) -> Dict[str, Any]: ...
    def copy_file(
        self,
        file_id: str,
        new_name: Optional[str] = None,
        parent_id: Optional[str] = None,
    ) -> Dict[str, Any]: ...

    def trash_file(self, file_id: str) -> Dict[str, Any]: ...
    def restore_file(self, file_id: str) -> Dict[str, Any]: ...
    def delete_file(self, file_id: str) -> Dict[str, Any]: ...

    # Folder Operations
    def create_folder(
        self,
        name: str,
        parent_id: Optional[str] = None,
    ) -> Dict[str, Any]: ...

    def get_folder_tree(
        self,
        folder_id: Optional[str] = None,
        max_depth: int = 3,
    ) -> Dict[str, Any]: ...

    def get_folder_path(self, folder_id: str) -> Dict[str, Any]: ...

    # Google Workspace Files
    def create_google_doc(
        self,
        name: str,
        parent_id: Optional[str] = None,
    ) -> Dict[str, Any]: ...

    def create_google_sheet(
        self,
        name: str,
        parent_id: Optional[str] = None,
    ) -> Dict[str, Any]: ...

    def create_google_slides(
        self,
        name: str,
        parent_id: Optional[str] = None,
    ) -> Dict[str, Any]: ...

    def export_google_file(
        self,
        file_id: str,
        export_format: str,
    ) -> Dict[str, Any]: ...

    # Sharing & Permissions
    def get_permissions(self, file_id: str) -> Dict[str, Any]: ...
    def share_file(
        self,
        file_id: str,
        email: Optional[str] = None,
        role: str = "reader",
        type: str = "user",
        domain: Optional[str] = None,
        send_notification: bool = True,
    ) -> Dict[str, Any]: ...

    def update_permission(
        self,
        file_id: str,
        permission_id: str,
        role: str,
    ) -> Dict[str, Any]: ...

    def remove_permission(
        self,
        file_id: str,
        permission_id: str,
    ) -> Dict[str, Any]: ...

    def transfer_ownership(
        self,
        file_id: str,
        new_owner_email: str,
    ) -> Dict[str, Any]: ...

    def create_shortcut(
        self,
        target_file_id: str,
        shortcut_name: str,
        parent_id: Optional[str] = None,
    ) -> Dict[str, Any]: ...

    # Quota
    def get_quota(self) -> Dict[str, Any]: ...

    # Shared Drives
    def list_shared_drives(
        self,
        page_size: int = 100,
        page_token: Optional[str] = None,
    ) -> Dict[str, Any]: ...

    def get_shared_drive(self, drive_id: str) -> Dict[str, Any]: ...
    def list_shared_drive_members(self, drive_id: str) -> Dict[str, Any]: ...

    # Bulk Operations
    def bulk_move(
        self,
        file_ids: List[str],
        new_parent_id: str,
    ) -> Dict[str, Any]: ...

    def bulk_trash(self, file_ids: List[str]) -> Dict[str, Any]: ...
    def bulk_delete(self, file_ids: List[str]) -> Dict[str, Any]: ...
    def bulk_share(
        self,
        file_ids: List[str],
        email: str,
        role: str = "reader",
    ) -> Dict[str, Any]: ...

    # Activity
    def get_activity(
        self,
        file_id: Optional[str] = None,
        page_size: int = 50,
    ) -> Dict[str, Any]: ...

    # Labels
    def list_labels(self) -> Dict[str, Any]: ...
    def get_label(self, label_id: str) -> Dict[str, Any]: ...
    def get_file_labels(self, file_id: str) -> Dict[str, Any]: ...
    def set_file_label(
        self,
        file_id: str,
        label_id: str,
        fields: Dict[str, Any],
    ) -> Dict[str, Any]: ...

    def remove_file_label(
        self,
        file_id: str,
        label_id: str,
    ) -> Dict[str, Any]: ...

    def search_by_label(
        self,
        label_id: str,
        field_id: Optional[str] = None,
        value: Optional[str] = None,
    ) -> Dict[str, Any]: ...

    # OCR
    def upload_with_ocr(
        self,
        file_path: str,
        name: Optional[str] = None,
        parent_id: Optional[str] = None,
        language: str = "en",
    ) -> Dict[str, Any]: ...

    def ocr_existing(
        self,
        file_id: str,
        language: str = "en",
    ) -> Dict[str, Any]: ...

def get_drive_processor() -> DriveProcessor: ...
