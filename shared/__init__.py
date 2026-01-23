"""
Shared utilities for gmail-mcp monorepo.

This package contains common code used across gmail-mcp, drive-mcp, and docs-mcp servers.
"""

from shared.types import (
    DriveUser,
    DriveFile,
    DrivePermission,
    DriveComment,
    DriveReply,
    DriveRevision,
    SharedDrive,
    DriveLabel,
    DriveFileLabel,
    DocContent,
    OcrResult,
    PdfMetadata,
    VaultExport,
    OperationResult,
)

__all__ = [
    "DriveUser",
    "DriveFile",
    "DrivePermission",
    "DriveComment",
    "DriveReply",
    "DriveRevision",
    "SharedDrive",
    "DriveLabel",
    "DriveFileLabel",
    "DocContent",
    "OcrResult",
    "PdfMetadata",
    "VaultExport",
    "OperationResult",
]
