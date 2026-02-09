"""
Drive Processor Module

This module provides functionality for interacting with the Google Drive API.
"""

import io
import json
import mimetypes
from typing import Any, Dict, List, Optional, Tuple

from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload, MediaFileUpload
from google.oauth2.credentials import Credentials

from gmail_mcp.utils.logger import get_logger
from gmail_mcp.auth.oauth import get_credentials

logger = get_logger("drive_mcp.processor")

# MIME type mappings for Google Workspace files
GOOGLE_MIME_TYPES = {
    "document": "application/vnd.google-apps.document",
    "spreadsheet": "application/vnd.google-apps.spreadsheet",
    "presentation": "application/vnd.google-apps.presentation",
    "folder": "application/vnd.google-apps.folder",
}

# Export MIME types for Google Workspace files
EXPORT_MIME_TYPES = {
    "application/vnd.google-apps.document": {
        "pdf": "application/pdf",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "txt": "text/plain",
        "html": "text/html",
        "md": "text/markdown",
    },
    "application/vnd.google-apps.spreadsheet": {
        "pdf": "application/pdf",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "csv": "text/csv",
    },
    "application/vnd.google-apps.presentation": {
        "pdf": "application/pdf",
        "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    },
}


class DriveProcessor:
    """
    Processor for Google Drive operations.
    """

    def __init__(self) -> None:
        """Initialize the Drive processor."""
        self._service = None
        self._docs_service = None

    def _get_service(self) -> Any:
        """
        Get the Google Drive API service.

        Returns:
            Any: The Google Drive API service.

        Raises:
            RuntimeError: If authentication fails.
        """
        if self._service is None:
            credentials = get_credentials()
            if not credentials:
                raise RuntimeError("Not authenticated with Google")
            self._service = build("drive", "v3", credentials=credentials)
        return self._service

    def _get_docs_service(self) -> Any:
        """
        Get the Google Docs API service.

        Returns:
            Any: The Google Docs API v1 service.

        Raises:
            RuntimeError: If authentication fails.
        """
        if self._docs_service is None:
            credentials = get_credentials()
            if not credentials:
                raise RuntimeError("Not authenticated with Google")
            self._docs_service = build("docs", "v1", credentials=credentials)
        return self._docs_service

    # =========================================================================
    # Core File Operations
    # =========================================================================

    def list_files(
        self,
        folder_id: Optional[str] = None,
        page_size: int = 10,
        page_token: Optional[str] = None,
        order_by: str = "modifiedTime desc",
    ) -> Dict[str, Any]:
        """
        List files in a folder or root.

        Args:
            folder_id: The ID of the folder to list. If None, lists root.
            page_size: Maximum number of files to return.
            page_token: Token for pagination.
            order_by: Sort order for results.

        Returns:
            Dict containing files list and nextPageToken if available.
        """
        service = self._get_service()

        query_parts = ["trashed = false"]
        if folder_id:
            query_parts.append(f"'{folder_id}' in parents")
        else:
            query_parts.append("'root' in parents")

        query = " and ".join(query_parts)

        fields = "nextPageToken, files(id, name, mimeType, size, createdTime, modifiedTime, parents, webViewLink, webContentLink, owners, shared, trashed)"

        request_params = {
            "q": query,
            "pageSize": page_size,
            "orderBy": order_by,
            "fields": fields,
        }

        if page_token:
            request_params["pageToken"] = page_token

        result = service.files().list(**request_params).execute()

        return {
            "files": result.get("files", []),
            "nextPageToken": result.get("nextPageToken"),
        }

    def search_files(
        self,
        query: Optional[str] = None,
        name: Optional[str] = None,
        mime_type: Optional[str] = None,
        full_text: Optional[str] = None,
        in_folder: Optional[str] = None,
        modified_after: Optional[str] = None,
        modified_before: Optional[str] = None,
        owner_email: Optional[str] = None,
        shared_with_me: Optional[bool] = None,
        page_size: int = 10,
        page_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Search for files using various criteria.

        Args:
            query: Raw query string (overrides other params if provided).
            name: Search by filename (contains).
            mime_type: Filter by MIME type.
            full_text: Full-text search in file content.
            in_folder: Limit search to a specific folder.
            modified_after: ISO date string for modified time filter.
            modified_before: ISO date string for modified time filter.
            owner_email: Filter by owner email.
            page_size: Maximum number of results.
            page_token: Token for pagination.

        Returns:
            Dict containing files list and nextPageToken if available.
        """
        service = self._get_service()

        if query:
            search_query = query
        else:
            query_parts = ["trashed = false"]

            if name:
                query_parts.append(f"name contains '{name}'")
            if mime_type:
                query_parts.append(f"mimeType = '{mime_type}'")
            if full_text:
                query_parts.append(f"fullText contains '{full_text}'")
            if in_folder:
                query_parts.append(f"'{in_folder}' in parents")
            if modified_after:
                query_parts.append(f"modifiedTime > '{modified_after}'")
            if modified_before:
                query_parts.append(f"modifiedTime < '{modified_before}'")
            if owner_email:
                query_parts.append(f"'{owner_email}' in owners")
            if shared_with_me:
                query_parts.append("sharedWithMe = true")

            search_query = " and ".join(query_parts)

        fields = "nextPageToken, files(id, name, mimeType, size, createdTime, modifiedTime, parents, webViewLink, webContentLink, owners, shared, trashed)"

        request_params = {
            "q": search_query,
            "pageSize": page_size,
            "fields": fields,
        }

        if page_token:
            request_params["pageToken"] = page_token

        result = service.files().list(**request_params).execute()

        return {
            "query": search_query,
            "files": result.get("files", []),
            "nextPageToken": result.get("nextPageToken"),
        }

    def get_file(self, file_id: str) -> Dict[str, Any]:
        """
        Get file metadata.

        Args:
            file_id: The ID of the file.

        Returns:
            Dict containing file metadata.
        """
        service = self._get_service()

        fields = "id, name, mimeType, size, createdTime, modifiedTime, parents, webViewLink, webContentLink, owners, shared, trashed, description, starred"

        result = service.files().get(fileId=file_id, fields=fields).execute()

        return result

    def read_file(self, file_id: str, export_format: Optional[str] = None) -> Tuple[bytes, str, str]:
        """
        Download/read file content.

        For Google Workspace files (Docs, Sheets, Slides), exports as appropriate format.
        For regular files, downloads the content.

        Args:
            file_id: The ID of the file.
            export_format: Export format for Google Workspace files (e.g., "txt", "pdf").

        Returns:
            Tuple of (content bytes, mime_type, filename).
        """
        service = self._get_service()

        # Get file metadata first
        file_meta = service.files().get(fileId=file_id, fields="name, mimeType").execute()
        mime_type = file_meta.get("mimeType", "")
        filename = file_meta.get("name", "")

        # Check if it's a Google Workspace file
        if mime_type in EXPORT_MIME_TYPES:
            # Use requested format, fall back to pdf
            fmt = export_format or "pdf"
            available = EXPORT_MIME_TYPES[mime_type]
            if fmt not in available:
                raise ValueError(
                    f"Format '{fmt}' not available for {mime_type}. "
                    f"Available: {list(available.keys())}"
                )
            export_mime = available[fmt]
            request = service.files().export_media(fileId=file_id, mimeType=export_mime)
            # CRITICAL: Return the export mime type, not the source mime type.
            # The tool layer uses this to decide text vs base64 encoding.
            mime_type = export_mime
        else:
            # Download regular file
            request = service.files().get_media(fileId=file_id)

        # Download the content
        buffer = io.BytesIO()
        downloader = MediaIoBaseDownload(buffer, request)

        done = False
        while not done:
            _, done = downloader.next_chunk()

        buffer.seek(0)
        return buffer.read(), mime_type, filename

    def create_file(
        self,
        name: str,
        content: bytes,
        mime_type: str,
        parent_id: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Upload a new file.

        Args:
            name: The filename.
            content: File content as bytes.
            mime_type: MIME type of the file.
            parent_id: ID of the parent folder. If None, uploads to root.
            description: Optional file description.

        Returns:
            Dict containing the created file metadata.
        """
        service = self._get_service()

        file_metadata: Dict[str, Any] = {"name": name}

        if parent_id:
            file_metadata["parents"] = [parent_id]
        if description:
            file_metadata["description"] = description

        media = MediaIoBaseUpload(io.BytesIO(content), mimetype=mime_type, resumable=True)

        result = (
            service.files()
            .create(body=file_metadata, media_body=media, fields="id, name, mimeType, webViewLink")
            .execute()
        )

        return result

    def update_file(
        self,
        file_id: str,
        content: Optional[bytes] = None,
        mime_type: Optional[str] = None,
        new_name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Update an existing file's content or metadata.

        Args:
            file_id: The ID of the file to update.
            content: New file content (optional).
            mime_type: MIME type if updating content.
            new_name: New filename (optional).
            description: New description (optional).

        Returns:
            Dict containing the updated file metadata.
        """
        service = self._get_service()

        file_metadata: Dict[str, Any] = {}
        if new_name:
            file_metadata["name"] = new_name
        if description is not None:
            file_metadata["description"] = description

        if content is not None and mime_type:
            media = MediaIoBaseUpload(io.BytesIO(content), mimetype=mime_type, resumable=True)
            result = (
                service.files()
                .update(
                    fileId=file_id,
                    body=file_metadata if file_metadata else None,
                    media_body=media,
                    fields="id, name, mimeType, modifiedTime, webViewLink",
                )
                .execute()
            )
        else:
            result = (
                service.files()
                .update(
                    fileId=file_id,
                    body=file_metadata,
                    fields="id, name, mimeType, modifiedTime, webViewLink",
                )
                .execute()
            )

        return result

    def rename_file(self, file_id: str, new_name: str) -> Dict[str, Any]:
        """
        Rename a file without moving it.

        Args:
            file_id: The ID of the file.
            new_name: The new filename.

        Returns:
            Dict containing the updated file metadata.
        """
        return self.update_file(file_id, new_name=new_name)

    def move_file(self, file_id: str, new_parent_id: str) -> Dict[str, Any]:
        """
        Move a file to a different folder.

        Args:
            file_id: The ID of the file.
            new_parent_id: The ID of the destination folder.

        Returns:
            Dict containing the updated file metadata.
        """
        service = self._get_service()

        # Get current parents
        file = service.files().get(fileId=file_id, fields="parents").execute()
        previous_parents = ",".join(file.get("parents", []))

        # Move the file
        result = (
            service.files()
            .update(
                fileId=file_id,
                addParents=new_parent_id,
                removeParents=previous_parents,
                fields="id, name, parents, webViewLink",
            )
            .execute()
        )

        return result

    def copy_file(
        self,
        file_id: str,
        new_name: Optional[str] = None,
        parent_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Copy a file.

        Args:
            file_id: The ID of the file to copy.
            new_name: Name for the copy (optional, defaults to "Copy of {original}").
            parent_id: Destination folder (optional, defaults to same folder).

        Returns:
            Dict containing the new file metadata.
        """
        service = self._get_service()

        body: Dict[str, Any] = {}
        if new_name:
            body["name"] = new_name
        if parent_id:
            body["parents"] = [parent_id]

        result = (
            service.files()
            .copy(fileId=file_id, body=body, fields="id, name, mimeType, webViewLink")
            .execute()
        )

        return result

    def trash_file(self, file_id: str) -> Dict[str, Any]:
        """
        Move a file to trash.

        Args:
            file_id: The ID of the file.

        Returns:
            Dict containing the result.
        """
        service = self._get_service()

        result = (
            service.files()
            .update(fileId=file_id, body={"trashed": True}, fields="id, name, trashed")
            .execute()
        )

        return {"success": True, "file": result}

    def restore_file(self, file_id: str) -> Dict[str, Any]:
        """
        Restore a file from trash.

        Args:
            file_id: The ID of the file.

        Returns:
            Dict containing the result.
        """
        service = self._get_service()

        result = (
            service.files()
            .update(fileId=file_id, body={"trashed": False}, fields="id, name, trashed")
            .execute()
        )

        return {"success": True, "file": result}

    def delete_file(self, file_id: str) -> Dict[str, Any]:
        """
        Permanently delete a file. THIS CANNOT BE UNDONE.

        Args:
            file_id: The ID of the file.

        Returns:
            Dict containing the result.
        """
        service = self._get_service()

        service.files().delete(fileId=file_id).execute()

        return {"success": True, "message": f"File {file_id} permanently deleted"}

    # =========================================================================
    # Folder Operations
    # =========================================================================

    def create_folder(
        self,
        name: str,
        parent_id: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a new folder.

        Args:
            name: The folder name.
            parent_id: ID of the parent folder. If None, creates in root.
            description: Optional folder description.

        Returns:
            Dict containing the created folder metadata.
        """
        service = self._get_service()

        file_metadata: Dict[str, Any] = {
            "name": name,
            "mimeType": GOOGLE_MIME_TYPES["folder"],
        }

        if parent_id:
            file_metadata["parents"] = [parent_id]
        if description:
            file_metadata["description"] = description

        result = (
            service.files()
            .create(body=file_metadata, fields="id, name, mimeType, webViewLink")
            .execute()
        )

        return result

    def get_folder_tree(
        self,
        folder_id: Optional[str] = None,
        max_depth: int = 3,
    ) -> Dict[str, Any]:
        """
        Get recursive folder structure.

        Args:
            folder_id: The root folder ID. If None, starts from root.
            max_depth: Maximum depth to recurse.

        Returns:
            Dict containing the folder tree.
        """
        service = self._get_service()

        def get_children(parent_id: str, depth: int) -> List[Dict[str, Any]]:
            if depth >= max_depth:
                return []

            query = f"'{parent_id}' in parents and trashed = false"
            result = (
                service.files()
                .list(q=query, fields="files(id, name, mimeType)", pageSize=100)
                .execute()
            )

            children = []
            for item in result.get("files", []):
                child: Dict[str, Any] = {
                    "id": item["id"],
                    "name": item["name"],
                    "mimeType": item["mimeType"],
                }
                if item["mimeType"] == GOOGLE_MIME_TYPES["folder"]:
                    child["children"] = get_children(item["id"], depth + 1)
                children.append(child)

            return children

        root_id = folder_id or "root"

        # Get root folder info
        if folder_id:
            root_info = service.files().get(fileId=folder_id, fields="id, name").execute()
        else:
            root_info = {"id": "root", "name": "My Drive"}

        return {
            "id": root_info["id"],
            "name": root_info["name"],
            "children": get_children(root_id, 0),
        }

    def get_folder_path(self, folder_id: str) -> List[Dict[str, str]]:
        """
        Get the full path to a folder (breadcrumb).

        Args:
            folder_id: The ID of the folder.

        Returns:
            List of dicts with id and name, from root to the folder.
        """
        service = self._get_service()

        path = []
        current_id = folder_id

        while current_id and current_id != "root":
            file = service.files().get(fileId=current_id, fields="id, name, parents").execute()
            path.insert(0, {"id": file["id"], "name": file["name"]})

            parents = file.get("parents", [])
            current_id = parents[0] if parents else None

        # Add root
        path.insert(0, {"id": "root", "name": "My Drive"})

        return path

    # =========================================================================
    # Google Workspace File Creation
    # =========================================================================

    def create_google_doc(
        self,
        name: str,
        parent_id: Optional[str] = None,
        content: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a new Google Doc.

        Args:
            name: The document name.
            parent_id: ID of the parent folder.
            content: Initial text content (optional).

        Returns:
            Dict containing the created document metadata.
        """
        service = self._get_service()

        file_metadata: Dict[str, Any] = {
            "name": name,
            "mimeType": GOOGLE_MIME_TYPES["document"],
        }

        if parent_id:
            file_metadata["parents"] = [parent_id]

        result = (
            service.files()
            .create(body=file_metadata, fields="id, name, mimeType, webViewLink")
            .execute()
        )

        # TODO: If content provided, use Docs API to insert content

        return result

    def create_google_sheet(
        self,
        name: str,
        parent_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a new Google Sheet.

        Args:
            name: The spreadsheet name.
            parent_id: ID of the parent folder.

        Returns:
            Dict containing the created spreadsheet metadata.
        """
        service = self._get_service()

        file_metadata: Dict[str, Any] = {
            "name": name,
            "mimeType": GOOGLE_MIME_TYPES["spreadsheet"],
        }

        if parent_id:
            file_metadata["parents"] = [parent_id]

        result = (
            service.files()
            .create(body=file_metadata, fields="id, name, mimeType, webViewLink")
            .execute()
        )

        return result

    def create_google_slides(
        self,
        name: str,
        parent_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a new Google Slides presentation.

        Args:
            name: The presentation name.
            parent_id: ID of the parent folder.

        Returns:
            Dict containing the created presentation metadata.
        """
        service = self._get_service()

        file_metadata: Dict[str, Any] = {
            "name": name,
            "mimeType": GOOGLE_MIME_TYPES["presentation"],
        }

        if parent_id:
            file_metadata["parents"] = [parent_id]

        result = (
            service.files()
            .create(body=file_metadata, fields="id, name, mimeType, webViewLink")
            .execute()
        )

        return result

    def create_formatted_doc(
        self,
        name: str,
        markdown_content: str,
        parent_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        DEPRECATED: Use docgen-mcp's create_google_doc tool instead.

        This function previously converted markdown to Google Docs format using a regex parser.
        That approach has been deprecated in favor of structured input via docgen-mcp.

        Args:
            name: The document name.
            markdown_content: Markdown-formatted content (DEPRECATED).
            parent_id: ID of the parent folder (optional).

        Returns:
            Dict containing deprecation notice and migration instructions.
        """
        return {
            "error": "DEPRECATED",
            "message": "create_formatted_doc is deprecated. Use docgen-mcp's create_google_doc tool instead.",
            "migration": {
                "tool": "create_google_doc",
                "mcp": "docgen-mcp",
                "input_format": "Structured sections array, NOT markdown strings",
                "example": {
                    "title": name,
                    "sections": [
                        {"type": "heading", "level": 1, "text": "Title"},
                        {"type": "paragraph", "content": "Body text"},
                        {"type": "bullet_list", "items": ["Item 1", "Item 2"]},
                    ],
                    "config": "pwp",
                    "folder_id": parent_id,
                },
            },
        }


    def export_google_file(
        self,
        file_id: str,
        export_format: str,
    ) -> Tuple[bytes, str, str]:
        """
        Export a Google Workspace file to a different format.

        Args:
            file_id: The ID of the file to export.
            export_format: The target format (pdf, docx, xlsx, pptx, csv, txt, html).

        Returns:
            Tuple of (content bytes, mime_type, suggested_extension).
        """
        service = self._get_service()

        # Get file metadata
        file_meta = service.files().get(fileId=file_id, fields="name, mimeType").execute()
        source_mime = file_meta.get("mimeType", "")
        filename = file_meta.get("name", "")

        if source_mime not in EXPORT_MIME_TYPES:
            raise ValueError(f"File type {source_mime} cannot be exported")

        format_lower = export_format.lower()
        available_formats = EXPORT_MIME_TYPES[source_mime]

        if format_lower not in available_formats:
            raise ValueError(
                f"Cannot export {source_mime} to {format_lower}. "
                f"Available formats: {list(available_formats.keys())}"
            )

        export_mime = available_formats[format_lower]

        request = service.files().export_media(fileId=file_id, mimeType=export_mime)

        buffer = io.BytesIO()
        downloader = MediaIoBaseDownload(buffer, request)

        done = False
        while not done:
            _, done = downloader.next_chunk()

        buffer.seek(0)
        return buffer.read(), export_mime, format_lower

    # =========================================================================
    # Sharing & Permissions
    # =========================================================================

    def get_permissions(self, file_id: str) -> List[Dict[str, Any]]:
        """
        List who has access to a file.

        Args:
            file_id: The ID of the file.

        Returns:
            List of permission objects.
        """
        service = self._get_service()

        result = (
            service.permissions()
            .list(fileId=file_id, fields="permissions(id, type, role, emailAddress, displayName)")
            .execute()
        )

        return result.get("permissions", [])

    def share_file(
        self,
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
            file_id: The ID of the file.
            email: Email address (for user/group type).
            role: Permission role (owner, organizer, fileOrganizer, writer, commenter, reader).
            permission_type: Type of permission (user, group, domain, anyone).
            domain: Domain name (for domain type).
            send_notification: Whether to send email notification.
            message: Custom message for the notification.

        Returns:
            Dict containing the created permission.
        """
        service = self._get_service()

        permission: Dict[str, Any] = {
            "type": permission_type,
            "role": role,
        }

        if permission_type in ("user", "group") and email:
            permission["emailAddress"] = email
        elif permission_type == "domain" and domain:
            permission["domain"] = domain

        result = (
            service.permissions()
            .create(
                fileId=file_id,
                body=permission,
                sendNotificationEmail=send_notification,
                emailMessage=message,
                fields="id, type, role, emailAddress, displayName",
            )
            .execute()
        )

        return result

    def update_permission(
        self,
        file_id: str,
        permission_id: str,
        role: str,
    ) -> Dict[str, Any]:
        """
        Change permission level for existing permission.

        Args:
            file_id: The ID of the file.
            permission_id: The ID of the permission to update.
            role: New role (writer, commenter, reader).

        Returns:
            Dict containing the updated permission.
        """
        service = self._get_service()

        result = (
            service.permissions()
            .update(
                fileId=file_id,
                permissionId=permission_id,
                body={"role": role},
                fields="id, type, role, emailAddress, displayName",
            )
            .execute()
        )

        return result

    def remove_permission(self, file_id: str, permission_id: str) -> Dict[str, Any]:
        """
        Revoke access from a file.

        Args:
            file_id: The ID of the file.
            permission_id: The ID of the permission to remove.

        Returns:
            Dict containing the result.
        """
        service = self._get_service()

        service.permissions().delete(fileId=file_id, permissionId=permission_id).execute()

        return {"success": True, "message": f"Permission {permission_id} removed"}

    def transfer_ownership(self, file_id: str, new_owner_email: str) -> Dict[str, Any]:
        """
        Transfer file ownership to another user.

        Args:
            file_id: The ID of the file.
            new_owner_email: Email of the new owner.

        Returns:
            Dict containing the result.
        """
        service = self._get_service()

        permission = {
            "type": "user",
            "role": "owner",
            "emailAddress": new_owner_email,
        }

        result = (
            service.permissions()
            .create(
                fileId=file_id,
                body=permission,
                transferOwnership=True,
                fields="id, type, role, emailAddress",
            )
            .execute()
        )

        return result

    def create_shortcut(
        self,
        target_file_id: str,
        name: str,
        parent_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a shortcut to a file in another location.

        Args:
            target_file_id: The ID of the target file.
            name: Name for the shortcut.
            parent_id: Where to create the shortcut.

        Returns:
            Dict containing the shortcut metadata.
        """
        service = self._get_service()

        file_metadata: Dict[str, Any] = {
            "name": name,
            "mimeType": "application/vnd.google-apps.shortcut",
            "shortcutDetails": {"targetId": target_file_id},
        }

        if parent_id:
            file_metadata["parents"] = [parent_id]

        result = (
            service.files()
            .create(body=file_metadata, fields="id, name, mimeType, webViewLink, shortcutDetails")
            .execute()
        )

        return result

    # =========================================================================
    # Storage & Quota
    # =========================================================================

    def get_quota(self) -> Dict[str, Any]:
        """
        Get storage usage and limits.

        Returns:
            Dict containing quota information.
        """
        service = self._get_service()

        about = service.about().get(fields="storageQuota, user").execute()

        quota = about.get("storageQuota", {})
        user = about.get("user", {})

        return {
            "user": {
                "displayName": user.get("displayName"),
                "emailAddress": user.get("emailAddress"),
            },
            "quota": {
                "limit": int(quota.get("limit", 0)),
                "usage": int(quota.get("usage", 0)),
                "usageInDrive": int(quota.get("usageInDrive", 0)),
                "usageInDriveTrash": int(quota.get("usageInDriveTrash", 0)),
            },
        }

    # =========================================================================
    # Shared Drives
    # =========================================================================

    def list_shared_drives(
        self,
        page_size: int = 10,
        page_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        List all shared drives the user can access.

        Args:
            page_size: Maximum number of shared drives to return.
            page_token: Token for pagination.

        Returns:
            Dict containing shared drives list and pagination token.
        """
        service = self._get_service()

        request_params = {
            "pageSize": page_size,
            "fields": "nextPageToken, drives(id, name, createdTime, hidden, restrictions)",
        }

        if page_token:
            request_params["pageToken"] = page_token

        result = service.drives().list(**request_params).execute()

        return {
            "drives": result.get("drives", []),
            "nextPageToken": result.get("nextPageToken"),
        }

    def get_shared_drive(self, drive_id: str) -> Dict[str, Any]:
        """
        Get shared drive details.

        Args:
            drive_id: The ID of the shared drive.

        Returns:
            Dict containing shared drive details.
        """
        service = self._get_service()

        result = (
            service.drives()
            .get(driveId=drive_id, fields="id, name, createdTime, hidden, restrictions, capabilities")
            .execute()
        )

        return result

    def list_shared_drive_members(
        self,
        drive_id: str,
        page_size: int = 100,
        page_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        List members of a shared drive.

        Args:
            drive_id: The ID of the shared drive.
            page_size: Maximum number of members to return.
            page_token: Token for pagination.

        Returns:
            Dict containing members list.
        """
        service = self._get_service()

        request_params = {
            "fileId": drive_id,
            "supportsAllDrives": True,
            "pageSize": page_size,
            "fields": "nextPageToken, permissions(id, type, role, emailAddress, displayName)",
        }

        if page_token:
            request_params["pageToken"] = page_token

        result = service.permissions().list(**request_params).execute()

        return {
            "members": result.get("permissions", []),
            "nextPageToken": result.get("nextPageToken"),
        }

    # =========================================================================
    # Bulk Operations
    # =========================================================================

    def bulk_move_files(
        self,
        file_ids: List[str],
        destination_folder_id: str,
    ) -> Dict[str, Any]:
        """
        Move multiple files to a folder.

        Args:
            file_ids: List of file IDs to move.
            destination_folder_id: ID of the destination folder.

        Returns:
            Dict containing results for each file.
        """
        service = self._get_service()
        results = {"success": [], "failed": []}

        for file_id in file_ids:
            try:
                # Get current parents
                file = service.files().get(fileId=file_id, fields="parents").execute()
                previous_parents = ",".join(file.get("parents", []))

                # Move the file
                service.files().update(
                    fileId=file_id,
                    addParents=destination_folder_id,
                    removeParents=previous_parents,
                    fields="id, name",
                ).execute()

                results["success"].append(file_id)
            except Exception as e:
                results["failed"].append({"file_id": file_id, "error": str(e)})

        return {
            "moved": len(results["success"]),
            "failed": len(results["failed"]),
            "results": results,
        }

    def bulk_trash_files(self, file_ids: List[str]) -> Dict[str, Any]:
        """
        Move multiple files to trash.

        Args:
            file_ids: List of file IDs to trash.

        Returns:
            Dict containing results for each file.
        """
        service = self._get_service()
        results = {"success": [], "failed": []}

        for file_id in file_ids:
            try:
                service.files().update(
                    fileId=file_id,
                    body={"trashed": True},
                    fields="id",
                ).execute()
                results["success"].append(file_id)
            except Exception as e:
                results["failed"].append({"file_id": file_id, "error": str(e)})

        return {
            "trashed": len(results["success"]),
            "failed": len(results["failed"]),
            "results": results,
        }

    def bulk_delete_files(self, file_ids: List[str]) -> Dict[str, Any]:
        """
        Permanently delete multiple files. THIS CANNOT BE UNDONE.

        Args:
            file_ids: List of file IDs to delete permanently.

        Returns:
            Dict containing results for each file.
        """
        service = self._get_service()
        results = {"success": [], "failed": []}

        for file_id in file_ids:
            try:
                service.files().delete(fileId=file_id).execute()
                results["success"].append(file_id)
            except Exception as e:
                results["failed"].append({"file_id": file_id, "error": str(e)})

        return {
            "deleted": len(results["success"]),
            "failed": len(results["failed"]),
            "results": results,
        }

    def bulk_share_files(
        self,
        file_ids: List[str],
        email: str,
        role: str = "reader",
        send_notification: bool = True,
    ) -> Dict[str, Any]:
        """
        Share multiple files with the same user.

        Args:
            file_ids: List of file IDs to share.
            email: Email address to share with.
            role: Permission role (reader, commenter, writer).
            send_notification: Whether to send email notification.

        Returns:
            Dict containing results for each file.
        """
        service = self._get_service()
        results = {"success": [], "failed": []}

        permission = {
            "type": "user",
            "role": role,
            "emailAddress": email,
        }

        for file_id in file_ids:
            try:
                service.permissions().create(
                    fileId=file_id,
                    body=permission,
                    sendNotificationEmail=send_notification,
                    fields="id",
                ).execute()
                results["success"].append(file_id)
            except Exception as e:
                results["failed"].append({"file_id": file_id, "error": str(e)})

        return {
            "shared": len(results["success"]),
            "failed": len(results["failed"]),
            "results": results,
        }

    # =========================================================================
    # Drive Activity
    # =========================================================================

    def get_drive_activity(
        self,
        file_id: Optional[str] = None,
        folder_id: Optional[str] = None,
        page_size: int = 10,
        page_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get recent activity on files.

        Requires Drive Activity API to be enabled.

        Args:
            file_id: Get activity for a specific file.
            folder_id: Get activity for files in a folder.
            page_size: Maximum number of activities to return.
            page_token: Token for pagination.

        Returns:
            Dict containing activity list.
        """
        # Note: This requires the Drive Activity API (driveactivity.googleapis.com)
        # which is a separate API from the Drive API
        try:
            from googleapiclient.discovery import build
            credentials = get_credentials()
            activity_service = build("driveactivity", "v2", credentials=credentials)

            request_body: Dict[str, Any] = {"pageSize": page_size}

            if file_id:
                request_body["itemName"] = f"items/{file_id}"
            elif folder_id:
                request_body["ancestorName"] = f"items/{folder_id}"

            if page_token:
                request_body["pageToken"] = page_token

            result = activity_service.activity().query(body=request_body).execute()

            # Simplify the activity data
            activities = []
            for activity in result.get("activities", []):
                simplified = {
                    "time": activity.get("timestamp"),
                    "actions": [],
                    "actors": [],
                    "targets": [],
                }

                for action in activity.get("actions", []):
                    action_type = next(iter(action.get("detail", {}).keys()), "unknown")
                    simplified["actions"].append(action_type)

                for actor in activity.get("actors", []):
                    if "user" in actor:
                        user = actor["user"].get("knownUser", {})
                        simplified["actors"].append(user.get("personName", "Unknown"))

                for target in activity.get("targets", []):
                    if "driveItem" in target:
                        item = target["driveItem"]
                        simplified["targets"].append({
                            "name": item.get("name", "Unknown"),
                            "title": item.get("title", "Unknown"),
                        })

                activities.append(simplified)

            return {
                "activities": activities,
                "nextPageToken": result.get("nextPageToken"),
            }

        except Exception as e:
            logger.warning(f"Drive Activity API error (may not be enabled): {e}")
            return {
                "error": str(e),
                "message": "Drive Activity API may not be enabled. Enable it at https://console.cloud.google.com/apis/library/driveactivity.googleapis.com",
                "activities": [],
            }

    # =========================================================================
    # Drive Labels (Google Workspace)
    # =========================================================================

    def _get_labels_service(self) -> Any:
        """Get the Drive Labels API service."""
        credentials = get_credentials()
        if not credentials:
            raise RuntimeError("Not authenticated with Google")
        return build("drivelabels", "v2", credentials=credentials)

    def list_drive_labels(
        self,
        page_size: int = 50,
        page_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        List available label definitions in the organization.

        Requires Google Workspace and Drive Labels API.

        Args:
            page_size: Maximum number of labels to return.
            page_token: Token for pagination.

        Returns:
            Dict containing labels list.
        """
        try:
            labels_service = self._get_labels_service()

            request_params = {
                "view": "LABEL_VIEW_FULL",
                "pageSize": page_size,
            }

            if page_token:
                request_params["pageToken"] = page_token

            result = labels_service.labels().list(**request_params).execute()

            return {
                "labels": result.get("labels", []),
                "nextPageToken": result.get("nextPageToken"),
            }

        except Exception as e:
            logger.warning(f"Drive Labels API error: {e}")
            return {
                "error": str(e),
                "message": "Drive Labels API may not be available. Requires Google Workspace.",
                "labels": [],
            }

    def get_drive_label(self, label_id: str) -> Dict[str, Any]:
        """
        Get label definition details.

        Args:
            label_id: The ID of the label.

        Returns:
            Dict containing label definition with fields and options.
        """
        try:
            labels_service = self._get_labels_service()

            result = (
                labels_service.labels()
                .get(name=f"labels/{label_id}", view="LABEL_VIEW_FULL")
                .execute()
            )

            return result

        except Exception as e:
            logger.warning(f"Drive Labels API error: {e}")
            return {"error": str(e)}

    def get_file_labels(self, file_id: str) -> Dict[str, Any]:
        """
        Get labels applied to a specific file.

        Args:
            file_id: The ID of the file.

        Returns:
            Dict containing the file's labels.
        """
        service = self._get_service()

        try:
            result = (
                service.files()
                .listLabels(fileId=file_id)
                .execute()
            )

            return {
                "labels": result.get("labels", []),
                "nextPageToken": result.get("nextPageToken"),
            }

        except Exception as e:
            logger.warning(f"Error getting file labels: {e}")
            return {"error": str(e), "labels": []}

    def set_file_label(
        self,
        file_id: str,
        label_id: str,
        fields: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Apply or update a label on a file.

        Args:
            file_id: The ID of the file.
            label_id: The ID of the label to apply.
            fields: Dict of field IDs to values.

        Returns:
            Dict containing the result.
        """
        service = self._get_service()

        try:
            label_modification = {
                "labelModifications": [
                    {
                        "labelId": label_id,
                        "fieldModifications": [
                            {"fieldId": k, "setTextField": {"values": [v]} if isinstance(v, str) else v}
                            for k, v in (fields or {}).items()
                        ] if fields else [],
                    }
                ]
            }

            result = (
                service.files()
                .modifyLabels(fileId=file_id, body=label_modification)
                .execute()
            )

            return {"success": True, "result": result}

        except Exception as e:
            logger.warning(f"Error setting file label: {e}")
            return {"success": False, "error": str(e)}

    def remove_file_label(self, file_id: str, label_id: str) -> Dict[str, Any]:
        """
        Remove a label from a file.

        Args:
            file_id: The ID of the file.
            label_id: The ID of the label to remove.

        Returns:
            Dict containing the result.
        """
        service = self._get_service()

        try:
            label_modification = {
                "labelModifications": [
                    {
                        "labelId": label_id,
                        "removeLabel": True,
                    }
                ]
            }

            result = (
                service.files()
                .modifyLabels(fileId=file_id, body=label_modification)
                .execute()
            )

            return {"success": True, "result": result}

        except Exception as e:
            logger.warning(f"Error removing file label: {e}")
            return {"success": False, "error": str(e)}

    def search_by_label(
        self,
        label_id: str,
        field_id: Optional[str] = None,
        field_value: Optional[str] = None,
        page_size: int = 10,
        page_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Search files by label values.

        Args:
            label_id: The ID of the label to search for.
            field_id: Optional field ID to filter by.
            field_value: Optional field value to match.
            page_size: Maximum number of results.
            page_token: Token for pagination.

        Returns:
            Dict containing matching files.
        """
        service = self._get_service()

        # Build the query
        if field_id and field_value:
            query = f"'labels/{label_id}.{field_id}' = '{field_value}'"
        else:
            query = f"'labels/{label_id}' in labels"

        query += " and trashed = false"

        try:
            request_params = {
                "q": query,
                "pageSize": page_size,
                "fields": "nextPageToken, files(id, name, mimeType, webViewLink)",
                "includeItemsFromAllDrives": True,
                "supportsAllDrives": True,
            }

            if page_token:
                request_params["pageToken"] = page_token

            result = service.files().list(**request_params).execute()

            return {
                "query": query,
                "files": result.get("files", []),
                "nextPageToken": result.get("nextPageToken"),
            }

        except Exception as e:
            logger.warning(f"Error searching by label: {e}")
            return {"error": str(e), "files": []}

    # =========================================================================
    # Drive OCR
    # =========================================================================

    def upload_image_with_ocr(
        self,
        name: str,
        content: bytes,
        mime_type: str,
        parent_id: Optional[str] = None,
        ocr_language: str = "en",
    ) -> Dict[str, Any]:
        """
        Upload an image and OCR it to a Google Doc.

        Uses Google Drive's native OCR capability.

        Args:
            name: Name for the resulting Google Doc.
            content: Image content as bytes.
            mime_type: MIME type of the image (image/png, image/jpeg, etc.).
            parent_id: ID of the parent folder.
            ocr_language: Language hint for OCR (default: "en").

        Returns:
            Dict containing the created Google Doc with OCR text.
        """
        service = self._get_service()

        file_metadata: Dict[str, Any] = {
            "name": name,
            "mimeType": GOOGLE_MIME_TYPES["document"],
        }

        if parent_id:
            file_metadata["parents"] = [parent_id]

        media = MediaIoBaseUpload(io.BytesIO(content), mimetype=mime_type, resumable=True)

        result = (
            service.files()
            .create(
                body=file_metadata,
                media_body=media,
                ocrLanguage=ocr_language,
                fields="id, name, mimeType, webViewLink",
            )
            .execute()
        )

        return {
            "success": True,
            "message": "Image uploaded and OCR'd to Google Doc",
            "file": result,
        }

    def ocr_existing_image(
        self,
        file_id: str,
        output_name: Optional[str] = None,
        parent_id: Optional[str] = None,
        ocr_language: str = "en",
    ) -> Dict[str, Any]:
        """
        OCR an existing image in Drive to a Google Doc.

        Args:
            file_id: ID of the image file in Drive.
            output_name: Name for the output Doc (default: original name + " (OCR)").
            parent_id: Where to create the output Doc.
            ocr_language: Language hint for OCR.

        Returns:
            Dict containing the created Google Doc.
        """
        service = self._get_service()

        # Get the original file
        original = service.files().get(fileId=file_id, fields="name, mimeType").execute()
        original_name = original.get("name", "Untitled")

        # Download the image
        request = service.files().get_media(fileId=file_id)
        buffer = io.BytesIO()
        downloader = MediaIoBaseDownload(buffer, request)

        done = False
        while not done:
            _, done = downloader.next_chunk()

        buffer.seek(0)
        content = buffer.read()

        # Upload with OCR
        doc_name = output_name or f"{original_name} (OCR)"
        return self.upload_image_with_ocr(
            name=doc_name,
            content=content,
            mime_type=original.get("mimeType", "image/png"),
            parent_id=parent_id,
            ocr_language=ocr_language,
        )

    def upload_pdf_with_ocr(
        self,
        name: str,
        content: bytes,
        parent_id: Optional[str] = None,
        ocr_language: str = "en",
    ) -> Dict[str, Any]:
        """
        Upload a PDF and OCR it to a Google Doc.

        Best for scanned PDFs. Native text PDFs may not need OCR.

        Args:
            name: Name for the resulting Google Doc.
            content: PDF content as bytes.
            parent_id: ID of the parent folder.
            ocr_language: Language hint for OCR.

        Returns:
            Dict containing the created Google Doc with OCR text.
        """
        service = self._get_service()

        file_metadata: Dict[str, Any] = {
            "name": name,
            "mimeType": GOOGLE_MIME_TYPES["document"],
        }

        if parent_id:
            file_metadata["parents"] = [parent_id]

        media = MediaIoBaseUpload(io.BytesIO(content), mimetype="application/pdf", resumable=True)

        result = (
            service.files()
            .create(
                body=file_metadata,
                media_body=media,
                ocrLanguage=ocr_language,
                fields="id, name, mimeType, webViewLink",
            )
            .execute()
        )

        return {
            "success": True,
            "message": "PDF uploaded and OCR'd to Google Doc",
            "file": result,
        }

    # =========================================================================
    # Star/Unstar Operations
    # =========================================================================

    def star_file(self, file_id: str) -> Dict[str, Any]:
        """
        Star a file for quick access.

        Args:
            file_id: The ID of the file to star.

        Returns:
            Dict containing success status and file info.
        """
        service = self._get_service()

        result = (
            service.files()
            .update(fileId=file_id, body={"starred": True}, fields="id, name, starred")
            .execute()
        )

        return {
            "success": True,
            "message": f"File '{result.get('name')}' starred",
            "file": result,
        }

    def unstar_file(self, file_id: str) -> Dict[str, Any]:
        """
        Remove star from a file.

        Args:
            file_id: The ID of the file to unstar.

        Returns:
            Dict containing success status and file info.
        """
        service = self._get_service()

        result = (
            service.files()
            .update(fileId=file_id, body={"starred": False}, fields="id, name, starred")
            .execute()
        )

        return {
            "success": True,
            "message": f"Star removed from '{result.get('name')}'",
            "file": result,
        }

    # =========================================================================
    # Comments Operations
    # =========================================================================

    def list_comments(
        self,
        file_id: str,
        page_size: int = 20,
        page_token: Optional[str] = None,
        include_deleted: bool = False,
    ) -> Dict[str, Any]:
        """
        List comments on a file.

        Args:
            file_id: The ID of the file.
            page_size: Maximum number of comments to return.
            page_token: Token for pagination.
            include_deleted: Whether to include deleted comments.

        Returns:
            Dict containing comments list and pagination token.
        """
        service = self._get_service()

        result = (
            service.comments()
            .list(
                fileId=file_id,
                pageSize=page_size,
                pageToken=page_token,
                includeDeleted=include_deleted,
                fields="comments(id, content, author, createdTime, modifiedTime, resolved, replies), nextPageToken",
            )
            .execute()
        )

        return {
            "success": True,
            "file_id": file_id,
            "comments": result.get("comments", []),
            "next_page_token": result.get("nextPageToken"),
        }

    def add_comment(
        self,
        file_id: str,
        content: str,
        anchor: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Add a comment to a file.

        Args:
            file_id: The ID of the file.
            content: The text content of the comment.
            anchor: Optional anchor for the comment (for specific location).

        Returns:
            Dict containing the created comment.
        """
        service = self._get_service()

        body: Dict[str, Any] = {"content": content}
        if anchor:
            body["anchor"] = anchor

        result = (
            service.comments()
            .create(
                fileId=file_id,
                body=body,
                fields="id, content, author, createdTime",
            )
            .execute()
        )

        return {
            "success": True,
            "message": "Comment added",
            "comment": result,
        }

    def delete_comment(self, file_id: str, comment_id: str) -> Dict[str, Any]:
        """
        Delete a comment from a file.

        Args:
            file_id: The ID of the file.
            comment_id: The ID of the comment to delete.

        Returns:
            Dict containing success status.
        """
        service = self._get_service()

        service.comments().delete(fileId=file_id, commentId=comment_id).execute()

        return {
            "success": True,
            "message": f"Comment {comment_id} deleted",
        }

    # =========================================================================
    # Revisions Operations
    # =========================================================================

    def list_revisions(
        self,
        file_id: str,
        page_size: int = 10,
        page_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        List revisions (version history) of a file.

        Args:
            file_id: The ID of the file.
            page_size: Maximum number of revisions to return.
            page_token: Token for pagination.

        Returns:
            Dict containing revisions list and pagination token.
        """
        service = self._get_service()

        result = (
            service.revisions()
            .list(
                fileId=file_id,
                pageSize=page_size,
                pageToken=page_token,
                fields="revisions(id, modifiedTime, lastModifyingUser, size, keepForever, publishAuto, published), nextPageToken",
            )
            .execute()
        )

        return {
            "success": True,
            "file_id": file_id,
            "revisions": result.get("revisions", []),
            "next_page_token": result.get("nextPageToken"),
        }

    def get_revision(self, file_id: str, revision_id: str) -> Dict[str, Any]:
        """
        Get metadata for a specific revision.

        Args:
            file_id: The ID of the file.
            revision_id: The ID of the revision.

        Returns:
            Dict containing revision metadata.
        """
        service = self._get_service()

        result = (
            service.revisions()
            .get(
                fileId=file_id,
                revisionId=revision_id,
                fields="id, modifiedTime, lastModifyingUser, size, keepForever, mimeType, originalFilename",
            )
            .execute()
        )

        return {
            "success": True,
            "revision": result,
        }

    def download_revision(
        self,
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
        service = self._get_service()

        request = service.revisions().get_media(fileId=file_id, revisionId=revision_id)

        with io.FileIO(output_path, "wb") as fh:
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()

        return {
            "success": True,
            "message": f"Revision downloaded to {output_path}",
            "output_path": output_path,
        }

    # =========================================================================
    # Shared Drive Admin Operations (Workspace only)
    # =========================================================================

    def create_shared_drive(self, name: str, request_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a new shared drive.

        Note: Requires Google Workspace admin permissions.

        Args:
            name: Name for the shared drive.
            request_id: Unique request ID for idempotency.

        Returns:
            Dict containing the created shared drive info.
        """
        import uuid
        service = self._get_service()

        if not request_id:
            request_id = str(uuid.uuid4())

        result = (
            service.drives()
            .create(
                requestId=request_id,
                body={"name": name},
                fields="id, name, createdTime",
            )
            .execute()
        )

        return {
            "success": True,
            "message": f"Shared drive '{name}' created",
            "drive": result,
        }

    def delete_shared_drive(self, drive_id: str) -> Dict[str, Any]:
        """
        Delete a shared drive.

        Note: Requires Google Workspace admin permissions.
        The drive must be empty.

        Args:
            drive_id: The ID of the shared drive to delete.

        Returns:
            Dict containing success status.
        """
        service = self._get_service()

        service.drives().delete(driveId=drive_id).execute()

        return {
            "success": True,
            "message": f"Shared drive {drive_id} deleted",
        }

    def update_shared_drive(
        self,
        drive_id: str,
        name: Optional[str] = None,
        restrictions: Optional[Dict[str, bool]] = None,
    ) -> Dict[str, Any]:
        """
        Update a shared drive's settings.

        Note: Requires Google Workspace admin permissions.

        Args:
            drive_id: The ID of the shared drive.
            name: New name for the drive (optional).
            restrictions: Dict of restriction settings (optional).
                - adminManagedRestrictions: bool
                - copyRequiresWriterPermission: bool
                - domainUsersOnly: bool
                - driveMembersOnly: bool

        Returns:
            Dict containing the updated shared drive info.
        """
        service = self._get_service()

        body: Dict[str, Any] = {}
        if name:
            body["name"] = name
        if restrictions:
            body["restrictions"] = restrictions

        if not body:
            return {
                "success": False,
                "error": "No updates specified",
            }

        result = (
            service.drives()
            .update(
                driveId=drive_id,
                body=body,
                fields="id, name, restrictions",
            )
            .execute()
        )

        return {
            "success": True,
            "message": "Shared drive updated",
            "drive": result,
        }

    # =========================================================================
    # Debug Tools
    # =========================================================================

    def debug_doc_structure(self, doc_id: str) -> Dict[str, Any]:
        """
        Debug: Get raw Google Docs structure including lists and paragraph bullets.

        Args:
            doc_id: The ID of the Google Doc to analyze.

        Returns:
            Dict containing lists object and paragraphs with bullets.
        """
        docs_service = self._get_docs_service()
        doc = docs_service.documents().get(documentId=doc_id).execute()

        # Extract lists object
        lists = doc.get('lists', {})
        lists_info = {}
        for list_id, list_def in lists.items():
            props = list_def.get('listProperties', {})
            nesting = props.get('nestingLevels', [])
            level0 = nesting[0] if nesting else {}
            lists_info[list_id] = {
                "glyphType": level0.get('glyphType'),
                "glyphFormat": level0.get('glyphFormat'),
                "startNumber": level0.get('startNumber', 1),
            }

        # Extract paragraphs with bullets
        paragraphs_with_bullets = []
        body = doc.get('body', {})
        for i, elem in enumerate(body.get('content', [])):
            if 'paragraph' in elem:
                para = elem['paragraph']
                bullet = para.get('bullet')
                if bullet:
                    # Get text content
                    text = ''
                    for pel in para.get('elements', []):
                        if 'textRun' in pel:
                            text += pel['textRun'].get('content', '')
                    text = text.strip()[:80]  # Truncate for display

                    paragraphs_with_bullets.append({
                        "index": i,
                        "listId": bullet.get('listId'),
                        "nestingLevel": bullet.get('nestingLevel', 0),
                        "text": text,
                    })

        return {
            "doc_id": doc_id,
            "title": doc.get('title', 'Unknown'),
            "list_count": len(lists),
            "lists": lists_info,
            "paragraphs_with_bullets": paragraphs_with_bullets,
            "analysis": f"Document has {len(lists)} list(s) and {len(paragraphs_with_bullets)} bulleted paragraphs",
        }


# Singleton instance
_processor: Optional[DriveProcessor] = None


def get_drive_processor() -> DriveProcessor:
    """
    Get the singleton DriveProcessor instance.

    Returns:
        DriveProcessor: The singleton instance.
    """
    global _processor
    if _processor is None:
        _processor = DriveProcessor()
    return _processor
