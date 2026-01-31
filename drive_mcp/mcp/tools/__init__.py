"""
MCP Tools for Drive MCP server.

This module provides all the tool definitions for the Drive MCP server.
"""

from typing import Any, Dict, List, Optional
import base64

from mcp.server.fastmcp import FastMCP

from gmail_mcp.utils.logger import get_logger
from drive_mcp.drive.processor import get_drive_processor

logger = get_logger("drive_mcp.tools")


def setup_tools(mcp: FastMCP) -> None:
    """
    Set up all Drive MCP tools.

    Args:
        mcp: The FastMCP application instance.
    """

    # =========================================================================
    # Core File Operations (12 tools)
    # =========================================================================

    @mcp.tool()
    def list_drive_files(
        folder_id: Optional[str] = None,
        max_results: int = 10,
        page_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        List files in a Google Drive folder.

        Args:
            folder_id: The ID of the folder to list. If not provided, lists root folder.
            max_results: Maximum number of files to return (default: 10, max: 100).
            page_token: Token for pagination to get next page of results.

        Returns:
            Dict containing:
                - files: List of file objects with metadata
                - next_page_token: Token for getting next page (if more results exist)
        """
        processor = get_drive_processor()
        return processor.list_files(
            folder_id=folder_id,
            page_size=min(max_results, 100),
            page_token=page_token,
        )

    @mcp.tool()
    def search_drive_files(
        query: Optional[str] = None,
        name: Optional[str] = None,
        mime_type: Optional[str] = None,
        full_text: Optional[str] = None,
        in_folder: Optional[str] = None,
        modified_after: Optional[str] = None,
        modified_before: Optional[str] = None,
        owner_email: Optional[str] = None,
        max_results: int = 10,
        page_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Search for files in Google Drive.

        Use either a raw query string OR the individual filter parameters.

        Args:
            query: Raw Drive API query string (overrides other params).
            name: Search files by name (contains match).
            mime_type: Filter by MIME type (e.g., "application/pdf").
            full_text: Full-text search in file content.
            in_folder: Limit search to files in a specific folder ID.
            modified_after: ISO date string (e.g., "2024-01-01T00:00:00Z").
            modified_before: ISO date string for upper bound.
            owner_email: Filter by owner's email address.
            max_results: Maximum number of results (default: 10, max: 100).
            page_token: Token for pagination.

        Returns:
            Dict containing:
                - query: The search query used
                - files: List of matching files
                - next_page_token: Token for next page (if exists)
        """
        processor = get_drive_processor()
        return processor.search_files(
            query=query,
            name=name,
            mime_type=mime_type,
            full_text=full_text,
            in_folder=in_folder,
            modified_after=modified_after,
            modified_before=modified_before,
            owner_email=owner_email,
            page_size=min(max_results, 100),
            page_token=page_token,
        )

    @mcp.tool()
    def get_drive_file(file_id: str) -> Dict[str, Any]:
        """
        Get detailed metadata for a specific file.

        Args:
            file_id: The ID of the file to get metadata for.

        Returns:
            Dict containing full file metadata including:
                - id, name, mimeType, size
                - createdTime, modifiedTime
                - parents, webViewLink
                - owners, shared, trashed
                - description, starred
        """
        processor = get_drive_processor()
        return processor.get_file(file_id)

    @mcp.tool()
    def read_drive_file(file_id: str) -> Dict[str, Any]:
        """
        Download and read the content of a file.

        For Google Workspace files (Docs, Sheets, Slides), exports as PDF.
        For text files, returns the text content.
        For binary files, returns base64-encoded content.

        Args:
            file_id: The ID of the file to read.

        Returns:
            Dict containing:
                - filename: Original filename
                - mime_type: MIME type of the file
                - content: File content (text for text files, base64 for binary)
                - encoding: "text" or "base64"
        """
        processor = get_drive_processor()
        content, mime_type, filename = processor.read_file(file_id)

        # Try to decode as text for text-based formats
        text_types = ["text/", "application/json", "application/xml"]
        is_text = any(mime_type.startswith(t) for t in text_types)

        if is_text:
            try:
                return {
                    "filename": filename,
                    "mime_type": mime_type,
                    "content": content.decode("utf-8"),
                    "encoding": "text",
                }
            except UnicodeDecodeError:
                pass

        # Return as base64 for binary content
        return {
            "filename": filename,
            "mime_type": mime_type,
            "content": base64.b64encode(content).decode("ascii"),
            "encoding": "base64",
        }

    @mcp.tool()
    def create_drive_file(
        name: str,
        content: str,
        mime_type: str = "text/plain",
        parent_id: Optional[str] = None,
        description: Optional[str] = None,
        encoding: str = "text",
    ) -> Dict[str, Any]:
        """
        Upload a new file to Google Drive.

        Args:
            name: The filename for the new file.
            content: File content (text or base64-encoded).
            mime_type: MIME type of the file (default: "text/plain").
            parent_id: ID of the parent folder. If not provided, uploads to root.
            description: Optional file description.
            encoding: Content encoding - "text" or "base64" (default: "text").

        Returns:
            Dict containing the created file metadata.
        """
        processor = get_drive_processor()

        if encoding == "base64":
            content_bytes = base64.b64decode(content)
        else:
            content_bytes = content.encode("utf-8")

        return processor.create_file(
            name=name,
            content=content_bytes,
            mime_type=mime_type,
            parent_id=parent_id,
            description=description,
        )

    @mcp.tool()
    def update_drive_file(
        file_id: str,
        content: Optional[str] = None,
        mime_type: Optional[str] = None,
        encoding: str = "text",
    ) -> Dict[str, Any]:
        """
        Update an existing file's content.

        Args:
            file_id: The ID of the file to update.
            content: New file content (text or base64-encoded).
            mime_type: MIME type (required if updating content).
            encoding: Content encoding - "text" or "base64" (default: "text").

        Returns:
            Dict containing the updated file metadata.
        """
        processor = get_drive_processor()

        content_bytes = None
        if content is not None:
            if encoding == "base64":
                content_bytes = base64.b64decode(content)
            else:
                content_bytes = content.encode("utf-8")

        return processor.update_file(
            file_id=file_id,
            content=content_bytes,
            mime_type=mime_type,
        )

    @mcp.tool()
    def rename_drive_file(file_id: str, new_name: str) -> Dict[str, Any]:
        """
        Rename a file without moving it.

        Args:
            file_id: The ID of the file to rename.
            new_name: The new filename.

        Returns:
            Dict containing the updated file metadata.
        """
        processor = get_drive_processor()
        return processor.rename_file(file_id, new_name)

    @mcp.tool()
    def move_drive_file(file_id: str, new_parent_id: str) -> Dict[str, Any]:
        """
        Move a file to a different folder.

        Args:
            file_id: The ID of the file to move.
            new_parent_id: The ID of the destination folder.

        Returns:
            Dict containing the updated file metadata.
        """
        processor = get_drive_processor()
        return processor.move_file(file_id, new_parent_id)

    @mcp.tool()
    def copy_drive_file(
        file_id: str,
        new_name: Optional[str] = None,
        parent_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Copy a file.

        Args:
            file_id: The ID of the file to copy.
            new_name: Name for the copy. If not provided, defaults to "Copy of {original}".
            parent_id: Destination folder. If not provided, copies to same folder.

        Returns:
            Dict containing the new file metadata.
        """
        processor = get_drive_processor()
        return processor.copy_file(file_id, new_name, parent_id)

    @mcp.tool()
    def trash_drive_file(file_id: str) -> Dict[str, Any]:
        """
        Move a file to trash.

        The file can be restored later using restore_drive_file.

        Args:
            file_id: The ID of the file to trash.

        Returns:
            Dict containing the result.
        """
        processor = get_drive_processor()
        return processor.trash_file(file_id)

    @mcp.tool()
    def restore_drive_file(file_id: str) -> Dict[str, Any]:
        """
        Restore a file from trash.

        Args:
            file_id: The ID of the trashed file to restore.

        Returns:
            Dict containing the result.
        """
        processor = get_drive_processor()
        return processor.restore_file(file_id)

    @mcp.tool()
    def delete_drive_file(file_id: str, confirm: bool = False) -> Dict[str, Any]:
        """
        Permanently delete a file. THIS CANNOT BE UNDONE.

        Args:
            file_id: The ID of the file to delete.
            confirm: Must be True to confirm deletion.

        Returns:
            Dict containing the result.
        """
        if not confirm:
            return {
                "success": False,
                "message": "Deletion not confirmed. Set confirm=True to permanently delete.",
            }
        processor = get_drive_processor()
        return processor.delete_file(file_id)

    # =========================================================================
    # Folder Operations (3 tools)
    # =========================================================================

    @mcp.tool()
    def create_drive_folder(
        name: str,
        parent_id: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a new folder in Google Drive.

        Args:
            name: The folder name.
            parent_id: ID of the parent folder. If not provided, creates in root.
            description: Optional folder description.

        Returns:
            Dict containing the created folder metadata.
        """
        processor = get_drive_processor()
        return processor.create_folder(name, parent_id, description)

    @mcp.tool()
    def get_folder_tree(
        folder_id: Optional[str] = None,
        max_depth: int = 3,
    ) -> Dict[str, Any]:
        """
        Get recursive folder structure.

        Args:
            folder_id: The root folder ID. If not provided, starts from root.
            max_depth: Maximum depth to recurse (default: 3, max: 5).

        Returns:
            Dict containing the folder tree with nested children.
        """
        processor = get_drive_processor()
        return processor.get_folder_tree(folder_id, min(max_depth, 5))

    @mcp.tool()
    def get_folder_path(folder_id: str) -> Dict[str, Any]:
        """
        Get the full path to a folder (breadcrumb).

        Args:
            folder_id: The ID of the folder.

        Returns:
            Dict containing the path as a list from root to the folder.
        """
        processor = get_drive_processor()
        path = processor.get_folder_path(folder_id)
        return {"path": path}

    # =========================================================================
    # Google Workspace File Creation (4 tools)
    # =========================================================================

    @mcp.tool()
    def create_google_doc(
        name: str,
        parent_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a new Google Doc.

        Args:
            name: The document name.
            parent_id: ID of the parent folder.

        Returns:
            Dict containing the created document metadata with webViewLink.
        """
        processor = get_drive_processor()
        return processor.create_google_doc(name, parent_id)

    @mcp.tool()
    def create_google_sheet(
        name: str,
        parent_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a new Google Sheet.

        Args:
            name: The spreadsheet name.
            parent_id: ID of the parent folder.

        Returns:
            Dict containing the created spreadsheet metadata with webViewLink.
        """
        processor = get_drive_processor()
        return processor.create_google_sheet(name, parent_id)

    @mcp.tool()
    def create_google_slides(
        name: str,
        parent_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a new Google Slides presentation.

        Args:
            name: The presentation name.
            parent_id: ID of the parent folder.

        Returns:
            Dict containing the created presentation metadata with webViewLink.
        """
        processor = get_drive_processor()
        return processor.create_google_slides(name, parent_id)

    @mcp.tool()
    def export_google_file(
        file_id: str,
        export_format: str,
    ) -> Dict[str, Any]:
        """
        Export a Google Workspace file to a different format.

        Supported exports:
        - Google Docs: pdf, docx, txt, html
        - Google Sheets: pdf, xlsx, csv
        - Google Slides: pdf, pptx

        Args:
            file_id: The ID of the Google Workspace file.
            export_format: Target format (pdf, docx, xlsx, pptx, csv, txt, html).

        Returns:
            Dict containing:
                - content: Base64-encoded file content
                - mime_type: MIME type of exported file
                - extension: File extension
        """
        processor = get_drive_processor()
        content, mime_type, extension = processor.export_google_file(file_id, export_format)

        return {
            "content": base64.b64encode(content).decode("ascii"),
            "mime_type": mime_type,
            "extension": extension,
            "encoding": "base64",
        }

    # =========================================================================
    # Sharing & Permissions (6 tools)
    # =========================================================================

    @mcp.tool()
    def get_drive_permissions(file_id: str) -> Dict[str, Any]:
        """
        List who has access to a file.

        Args:
            file_id: The ID of the file.

        Returns:
            Dict containing list of permissions with type, role, and user info.
        """
        processor = get_drive_processor()
        permissions = processor.get_permissions(file_id)
        return {"permissions": permissions}

    @mcp.tool()
    def share_drive_file(
        file_id: str,
        email: Optional[str] = None,
        role: str = "reader",
        permission_type: str = "user",
        domain: Optional[str] = None,
        send_notification: bool = True,
        message: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Share a file with a user, group, domain, or anyone.

        Args:
            file_id: The ID of the file to share.
            email: Email address (required for user/group type).
            role: Permission level - "reader", "commenter", "writer", or "owner".
            permission_type: Type of share - "user", "group", "domain", or "anyone".
            domain: Domain name (required for domain type).
            send_notification: Whether to send email notification (default: True).
            message: Custom message for the notification email.

        Returns:
            Dict containing the created permission.
        """
        processor = get_drive_processor()
        return processor.share_file(
            file_id=file_id,
            email=email,
            role=role,
            permission_type=permission_type,
            domain=domain,
            send_notification=send_notification,
            message=message,
        )

    @mcp.tool()
    def update_drive_permission(
        file_id: str,
        permission_id: str,
        role: str,
    ) -> Dict[str, Any]:
        """
        Change permission level for an existing share.

        Args:
            file_id: The ID of the file.
            permission_id: The ID of the permission to update (from get_drive_permissions).
            role: New role - "reader", "commenter", or "writer".

        Returns:
            Dict containing the updated permission.
        """
        processor = get_drive_processor()
        return processor.update_permission(file_id, permission_id, role)

    @mcp.tool()
    def remove_drive_permission(file_id: str, permission_id: str) -> Dict[str, Any]:
        """
        Revoke access to a file.

        Args:
            file_id: The ID of the file.
            permission_id: The ID of the permission to remove.

        Returns:
            Dict containing the result.
        """
        processor = get_drive_processor()
        return processor.remove_permission(file_id, permission_id)

    @mcp.tool()
    def transfer_drive_ownership(file_id: str, new_owner_email: str) -> Dict[str, Any]:
        """
        Transfer file ownership to another user.

        Args:
            file_id: The ID of the file.
            new_owner_email: Email address of the new owner.

        Returns:
            Dict containing the result.
        """
        processor = get_drive_processor()
        return processor.transfer_ownership(file_id, new_owner_email)

    @mcp.tool()
    def create_drive_shortcut(
        target_file_id: str,
        name: str,
        parent_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a shortcut to a file in another location.

        Args:
            target_file_id: The ID of the file to create a shortcut to.
            name: Name for the shortcut.
            parent_id: Where to create the shortcut.

        Returns:
            Dict containing the shortcut metadata.
        """
        processor = get_drive_processor()
        return processor.create_shortcut(target_file_id, name, parent_id)

    # =========================================================================
    # Storage & Quota (1 tool)
    # =========================================================================

    @mcp.tool()
    def get_drive_quota() -> Dict[str, Any]:
        """
        Check storage usage and limits.

        Returns:
            Dict containing:
                - user: User info (name, email)
                - quota: Storage quota info (limit, usage, usageInDrive, usageInDriveTrash)
        """
        processor = get_drive_processor()
        return processor.get_quota()

    # =========================================================================
    # Shared Drives (3 tools)
    # =========================================================================

    @mcp.tool()
    def list_shared_drives(
        max_results: int = 10,
        page_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        List all Shared Drives the user can access.

        Shared Drives are team-owned storage spaces (Google Workspace feature).

        Args:
            max_results: Maximum number of drives to return (default: 10).
            page_token: Token for pagination.

        Returns:
            Dict containing:
                - drives: List of Shared Drives with id, name, createdTime
                - next_page_token: Token for next page (if exists)
        """
        processor = get_drive_processor()
        return processor.list_shared_drives(page_size=max_results, page_token=page_token)

    @mcp.tool()
    def get_shared_drive(drive_id: str) -> Dict[str, Any]:
        """
        Get details of a specific Shared Drive.

        Args:
            drive_id: The ID of the Shared Drive.

        Returns:
            Dict containing Shared Drive details including restrictions and capabilities.
        """
        processor = get_drive_processor()
        return processor.get_shared_drive(drive_id)

    @mcp.tool()
    def list_shared_drive_members(
        drive_id: str,
        max_results: int = 100,
        page_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        List members of a Shared Drive and their roles.

        Args:
            drive_id: The ID of the Shared Drive.
            max_results: Maximum number of members to return (default: 100).
            page_token: Token for pagination.

        Returns:
            Dict containing:
                - members: List of members with type, role, email, name
                - next_page_token: Token for next page (if exists)
        """
        processor = get_drive_processor()
        return processor.list_shared_drive_members(
            drive_id=drive_id,
            page_size=max_results,
            page_token=page_token,
        )

    # =========================================================================
    # Bulk Operations (4 tools)
    # =========================================================================

    @mcp.tool()
    def bulk_move_files(
        file_ids: List[str],
        destination_folder_id: str,
    ) -> Dict[str, Any]:
        """
        Move multiple files to a folder at once.

        Args:
            file_ids: List of file IDs to move.
            destination_folder_id: ID of the destination folder.

        Returns:
            Dict containing:
                - moved: Number of successfully moved files
                - failed: Number of failed moves
                - results: Detailed success/failure for each file
        """
        processor = get_drive_processor()
        return processor.bulk_move_files(file_ids, destination_folder_id)

    @mcp.tool()
    def bulk_trash_files(file_ids: List[str]) -> Dict[str, Any]:
        """
        Move multiple files to trash at once.

        Args:
            file_ids: List of file IDs to trash.

        Returns:
            Dict containing:
                - trashed: Number of successfully trashed files
                - failed: Number of failed operations
                - results: Detailed success/failure for each file
        """
        processor = get_drive_processor()
        return processor.bulk_trash_files(file_ids)

    @mcp.tool()
    def bulk_delete_files(file_ids: List[str], confirm: bool = False) -> Dict[str, Any]:
        """
        Permanently delete multiple files. THIS CANNOT BE UNDONE.

        Args:
            file_ids: List of file IDs to permanently delete.
            confirm: Must be True to confirm deletion.

        Returns:
            Dict containing:
                - deleted: Number of successfully deleted files
                - failed: Number of failed deletions
                - results: Detailed success/failure for each file
        """
        if not confirm:
            return {
                "success": False,
                "message": "Bulk deletion not confirmed. Set confirm=True to permanently delete all files.",
            }
        processor = get_drive_processor()
        return processor.bulk_delete_files(file_ids)

    @mcp.tool()
    def bulk_share_files(
        file_ids: List[str],
        email: str,
        role: str = "reader",
        send_notification: bool = True,
    ) -> Dict[str, Any]:
        """
        Share multiple files with the same user at once.

        Args:
            file_ids: List of file IDs to share.
            email: Email address to share with.
            role: Permission role - "reader", "commenter", or "writer" (default: "reader").
            send_notification: Whether to send email notification (default: True).

        Returns:
            Dict containing:
                - shared: Number of successfully shared files
                - failed: Number of failed shares
                - results: Detailed success/failure for each file
        """
        processor = get_drive_processor()
        return processor.bulk_share_files(
            file_ids=file_ids,
            email=email,
            role=role,
            send_notification=send_notification,
        )

    # =========================================================================
    # Drive Activity (1 tool)
    # =========================================================================

    @mcp.tool()
    def get_drive_activity(
        file_id: Optional[str] = None,
        folder_id: Optional[str] = None,
        max_results: int = 10,
        page_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get recent activity on Drive files.

        Shows who did what to which files. Requires Drive Activity API enabled.

        Args:
            file_id: Get activity for a specific file (optional).
            folder_id: Get activity for files in a folder (optional).
            max_results: Maximum number of activities to return (default: 10).
            page_token: Token for pagination.

        Returns:
            Dict containing:
                - activities: List of activities with time, actions, actors, targets
                - next_page_token: Token for next page (if exists)
        """
        processor = get_drive_processor()
        return processor.get_drive_activity(
            file_id=file_id,
            folder_id=folder_id,
            page_size=max_results,
            page_token=page_token,
        )

    # =========================================================================
    # Drive Labels (6 tools) - Google Workspace
    # =========================================================================

    @mcp.tool()
    def list_drive_labels(
        max_results: int = 50,
        page_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        List available Drive label definitions in the organization.

        Drive Labels are metadata schemas for categorizing files (Google Workspace feature).

        Args:
            max_results: Maximum number of labels to return (default: 50).
            page_token: Token for pagination.

        Returns:
            Dict containing:
                - labels: List of label definitions
                - next_page_token: Token for next page (if exists)
        """
        processor = get_drive_processor()
        return processor.list_drive_labels(page_size=max_results, page_token=page_token)

    @mcp.tool()
    def get_drive_label(label_id: str) -> Dict[str, Any]:
        """
        Get details of a specific Drive label definition.

        Args:
            label_id: The ID of the label.

        Returns:
            Dict containing label definition with fields, options, and constraints.
        """
        processor = get_drive_processor()
        return processor.get_drive_label(label_id)

    @mcp.tool()
    def get_file_labels(file_id: str) -> Dict[str, Any]:
        """
        Get labels applied to a specific file.

        Args:
            file_id: The ID of the file.

        Returns:
            Dict containing:
                - labels: List of labels applied to the file with their field values
        """
        processor = get_drive_processor()
        return processor.get_file_labels(file_id)

    @mcp.tool()
    def set_file_label(
        file_id: str,
        label_id: str,
        fields: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Apply or update a label on a file.

        Args:
            file_id: The ID of the file.
            label_id: The ID of the label to apply.
            fields: Optional dict of field IDs to values for the label.

        Returns:
            Dict containing the result of the operation.
        """
        processor = get_drive_processor()
        return processor.set_file_label(file_id, label_id, fields)

    @mcp.tool()
    def remove_file_label(file_id: str, label_id: str) -> Dict[str, Any]:
        """
        Remove a label from a file.

        Args:
            file_id: The ID of the file.
            label_id: The ID of the label to remove.

        Returns:
            Dict containing the result of the operation.
        """
        processor = get_drive_processor()
        return processor.remove_file_label(file_id, label_id)

    @mcp.tool()
    def search_by_label(
        label_id: str,
        field_id: Optional[str] = None,
        field_value: Optional[str] = None,
        max_results: int = 10,
        page_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Search for files by label and optionally by field value.

        Args:
            label_id: The ID of the label to search for.
            field_id: Optional field ID to filter by.
            field_value: Optional field value to match.
            max_results: Maximum number of results (default: 10).
            page_token: Token for pagination.

        Returns:
            Dict containing:
                - query: The search query used
                - files: List of matching files
                - next_page_token: Token for next page (if exists)
        """
        processor = get_drive_processor()
        return processor.search_by_label(
            label_id=label_id,
            field_id=field_id,
            field_value=field_value,
            page_size=max_results,
            page_token=page_token,
        )

    # =========================================================================
    # Drive OCR (3 tools)
    # =========================================================================

    @mcp.tool()
    def upload_image_with_ocr(
        name: str,
        content: str,
        mime_type: str = "image/png",
        parent_id: Optional[str] = None,
        ocr_language: str = "en",
    ) -> Dict[str, Any]:
        """
        Upload an image and OCR it to a Google Doc.

        Uses Google Drive's native OCR. The image is converted to a Google Doc
        with the extracted text.

        Args:
            name: Name for the resulting Google Doc.
            content: Base64-encoded image content.
            mime_type: MIME type of the image (default: "image/png").
            parent_id: ID of the parent folder (optional).
            ocr_language: Language hint for OCR (default: "en").

        Returns:
            Dict containing the created Google Doc metadata with webViewLink.
        """
        processor = get_drive_processor()
        content_bytes = base64.b64decode(content)
        return processor.upload_image_with_ocr(
            name=name,
            content=content_bytes,
            mime_type=mime_type,
            parent_id=parent_id,
            ocr_language=ocr_language,
        )

    @mcp.tool()
    def ocr_existing_image(
        file_id: str,
        output_name: Optional[str] = None,
        parent_id: Optional[str] = None,
        ocr_language: str = "en",
    ) -> Dict[str, Any]:
        """
        OCR an existing image in Drive to a Google Doc.

        Creates a new Google Doc with the extracted text from the image.

        Args:
            file_id: ID of the image file in Drive.
            output_name: Name for the output Doc (default: original name + " (OCR)").
            parent_id: Where to create the output Doc (optional).
            ocr_language: Language hint for OCR (default: "en").

        Returns:
            Dict containing the created Google Doc metadata.
        """
        processor = get_drive_processor()
        return processor.ocr_existing_image(
            file_id=file_id,
            output_name=output_name,
            parent_id=parent_id,
            ocr_language=ocr_language,
        )

    @mcp.tool()
    def upload_pdf_with_ocr(
        name: str,
        content: str,
        parent_id: Optional[str] = None,
        ocr_language: str = "en",
    ) -> Dict[str, Any]:
        """
        Upload a scanned PDF and OCR it to a Google Doc.

        Best for scanned PDFs where text needs to be extracted.
        Native text PDFs may not need OCR.

        Args:
            name: Name for the resulting Google Doc.
            content: Base64-encoded PDF content.
            parent_id: ID of the parent folder (optional).
            ocr_language: Language hint for OCR (default: "en").

        Returns:
            Dict containing the created Google Doc metadata with webViewLink.
        """
        processor = get_drive_processor()
        content_bytes = base64.b64decode(content)
        return processor.upload_pdf_with_ocr(
            name=name,
            content=content_bytes,
            parent_id=parent_id,
            ocr_language=ocr_language,
        )

    # =========================================================================
    # Star/Unstar Operations (2 tools)
    # =========================================================================

    @mcp.tool()
    def star_drive_file(file_id: str) -> Dict[str, Any]:
        """
        Star a file for quick access.

        Starred files appear in the "Starred" section in Google Drive.

        Args:
            file_id: The ID of the file to star.

        Returns:
            Dict containing success status and file info.
        """
        processor = get_drive_processor()
        return processor.star_file(file_id)

    @mcp.tool()
    def unstar_drive_file(file_id: str) -> Dict[str, Any]:
        """
        Remove star from a file.

        Args:
            file_id: The ID of the file to unstar.

        Returns:
            Dict containing success status and file info.
        """
        processor = get_drive_processor()
        return processor.unstar_file(file_id)

    # =========================================================================
    # Comments Operations (3 tools)
    # =========================================================================

    @mcp.tool()
    def list_drive_comments(
        file_id: str,
        max_results: int = 20,
        page_token: Optional[str] = None,
        include_deleted: bool = False,
    ) -> Dict[str, Any]:
        """
        List comments on a file.

        Args:
            file_id: The ID of the file.
            max_results: Maximum number of comments to return (default: 20).
            page_token: Token for pagination.
            include_deleted: Whether to include deleted comments.

        Returns:
            Dict containing:
                - comments: List of comment objects
                - next_page_token: Token for next page (if exists)
        """
        processor = get_drive_processor()
        return processor.list_comments(
            file_id=file_id,
            page_size=max_results,
            page_token=page_token,
            include_deleted=include_deleted,
        )

    @mcp.tool()
    def add_drive_comment(
        file_id: str,
        content: str,
    ) -> Dict[str, Any]:
        """
        Add a comment to a file.

        Args:
            file_id: The ID of the file.
            content: The text content of the comment.

        Returns:
            Dict containing the created comment.
        """
        processor = get_drive_processor()
        return processor.add_comment(file_id=file_id, content=content)

    @mcp.tool()
    def delete_drive_comment(file_id: str, comment_id: str) -> Dict[str, Any]:
        """
        Delete a comment from a file.

        Args:
            file_id: The ID of the file.
            comment_id: The ID of the comment to delete.

        Returns:
            Dict containing success status.
        """
        processor = get_drive_processor()
        return processor.delete_comment(file_id=file_id, comment_id=comment_id)

    # =========================================================================
    # Revisions Operations (3 tools)
    # =========================================================================

    @mcp.tool()
    def list_drive_revisions(
        file_id: str,
        max_results: int = 10,
        page_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        List revisions (version history) of a file.

        Args:
            file_id: The ID of the file.
            max_results: Maximum number of revisions to return (default: 10).
            page_token: Token for pagination.

        Returns:
            Dict containing:
                - revisions: List of revision objects with metadata
                - next_page_token: Token for next page (if exists)
        """
        processor = get_drive_processor()
        return processor.list_revisions(
            file_id=file_id,
            page_size=max_results,
            page_token=page_token,
        )

    @mcp.tool()
    def get_drive_revision(file_id: str, revision_id: str) -> Dict[str, Any]:
        """
        Get metadata for a specific revision.

        Args:
            file_id: The ID of the file.
            revision_id: The ID of the revision.

        Returns:
            Dict containing revision metadata.
        """
        processor = get_drive_processor()
        return processor.get_revision(file_id=file_id, revision_id=revision_id)

    @mcp.tool()
    def download_drive_revision(
        file_id: str,
        revision_id: str,
        output_path: str,
    ) -> Dict[str, Any]:
        """
        Download a specific revision of a file.

        Args:
            file_id: The ID of the file.
            revision_id: The ID of the revision.
            output_path: Path to save the downloaded file.

        Returns:
            Dict containing success status and output path.
        """
        processor = get_drive_processor()
        return processor.download_revision(
            file_id=file_id,
            revision_id=revision_id,
            output_path=output_path,
        )

    # =========================================================================
    # Shared Drive Admin Operations (3 tools) - Workspace only
    # =========================================================================

    @mcp.tool()
    def create_shared_drive(name: str) -> Dict[str, Any]:
        """
        Create a new shared drive.

        Note: Requires Google Workspace admin permissions.
        Will fail for personal Gmail accounts.

        Args:
            name: Name for the shared drive.

        Returns:
            Dict containing the created shared drive info.
        """
        processor = get_drive_processor()
        return processor.create_shared_drive(name=name)

    @mcp.tool()
    def delete_shared_drive(drive_id: str) -> Dict[str, Any]:
        """
        Delete a shared drive.

        Note: Requires Google Workspace admin permissions.
        The drive must be empty before deletion.

        Args:
            drive_id: The ID of the shared drive to delete.

        Returns:
            Dict containing success status.
        """
        processor = get_drive_processor()
        return processor.delete_shared_drive(drive_id=drive_id)

    @mcp.tool()
    def update_shared_drive(
        drive_id: str,
        name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Update a shared drive's name.

        Note: Requires Google Workspace admin permissions.

        Args:
            drive_id: The ID of the shared drive.
            name: New name for the drive.

        Returns:
            Dict containing the updated shared drive info.
        """
        processor = get_drive_processor()
        return processor.update_shared_drive(drive_id=drive_id, name=name)

    logger.info("Drive MCP tools registered successfully")
