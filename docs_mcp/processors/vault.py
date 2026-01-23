"""
Vault Processor

Handles integration with Obsidian vaults for document storage.
"""

import os
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger("docs_mcp.processors.vault")


class VaultProcessor:
    """
    Processor for Obsidian vault integration.
    """

    def __init__(self, vault_path: Optional[str] = None):
        """
        Initialize the vault processor.

        Args:
            vault_path: Path to the Obsidian vault (or set VAULT_PATH env var).
        """
        self.vault_path = vault_path or os.getenv("VAULT_PATH", "")

    def _get_vault_path(self, override_path: Optional[str] = None) -> Path:
        """Get the vault path, raising an error if not configured."""
        path = override_path or self.vault_path
        if not path:
            raise ValueError(
                "Vault path not configured. Set VAULT_PATH environment variable "
                "or pass vault_path parameter."
            )
        return Path(path).expanduser()

    def _sanitize_filename(self, name: str) -> str:
        """Sanitize a string for use as a filename."""
        # Remove or replace invalid characters
        invalid_chars = r'[<>:"/\\|?*]'
        sanitized = re.sub(invalid_chars, "-", name)
        # Collapse multiple dashes
        sanitized = re.sub(r"-+", "-", sanitized)
        # Remove leading/trailing dashes and spaces
        sanitized = sanitized.strip("- ")
        return sanitized[:200]  # Limit length

    def _create_frontmatter(
        self,
        source: str,
        original_path: Optional[str] = None,
        tags: Optional[List[str]] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Create YAML frontmatter for a vault note."""
        lines = ["---"]
        lines.append("type: doc-import")
        lines.append(f"source: {source}")
        if original_path:
            lines.append(f"original_path: \"{original_path}\"")
        lines.append(f"imported: {datetime.now().strftime('%Y-%m-%d')}")

        all_tags = ["doc-import"]
        if tags:
            all_tags.extend(tags)
        lines.append(f"tags: [{', '.join(all_tags)}]")

        if extra:
            for key, value in extra.items():
                if isinstance(value, str):
                    lines.append(f"{key}: \"{value}\"")
                else:
                    lines.append(f"{key}: {value}")

        lines.append("---")
        return "\n".join(lines)

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
    ) -> Dict[str, Any]:
        """
        Save content to an Obsidian vault as a markdown file.

        Args:
            content: The markdown content to save.
            filename: Name for the file (without .md extension).
            vault_path: Override vault path.
            folder: Folder within vault (default: "0-inbox").
            source: Source identifier for frontmatter.
            original_path: Original file path for frontmatter.
            tags: Additional tags for frontmatter.
            frontmatter_extra: Additional frontmatter fields.

        Returns:
            Dict with success status and file path.
        """
        try:
            vault = self._get_vault_path(vault_path)
            target_folder = vault / folder
            target_folder.mkdir(parents=True, exist_ok=True)

            safe_filename = self._sanitize_filename(filename)
            target_file = target_folder / f"{safe_filename}.md"

            # Handle duplicate filenames
            counter = 1
            while target_file.exists():
                target_file = target_folder / f"{safe_filename}_{counter}.md"
                counter += 1

            # Create frontmatter
            frontmatter = self._create_frontmatter(
                source=source,
                original_path=original_path,
                tags=tags,
                extra=frontmatter_extra,
            )

            # Write file
            full_content = f"{frontmatter}\n\n{content}"
            target_file.write_text(full_content, encoding="utf-8")

            return {
                "success": True,
                "file_path": str(target_file),
                "filename": target_file.name,
                "folder": folder,
            }

        except Exception as e:
            logger.error(f"Error saving to vault: {e}")
            return {"error": str(e)}

    def save_file_to_vault(
        self,
        file_path: Union[str, Path],
        vault_path: Optional[str] = None,
        folder: str = "0-inbox",
        tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Save any file to the vault (copies the file as-is for non-text files).

        Args:
            file_path: Path to the file to save.
            vault_path: Override vault path.
            folder: Folder within vault.
            tags: Additional tags for sidecar metadata.

        Returns:
            Dict with success status and file path.
        """
        try:
            source_path = Path(file_path)
            if not source_path.exists():
                return {"error": f"File not found: {file_path}"}

            vault = self._get_vault_path(vault_path)
            target_folder = vault / folder
            target_folder.mkdir(parents=True, exist_ok=True)

            # Copy file
            target_file = target_folder / source_path.name

            # Handle duplicate filenames
            counter = 1
            stem = source_path.stem
            suffix = source_path.suffix
            while target_file.exists():
                target_file = target_folder / f"{stem}_{counter}{suffix}"
                counter += 1

            import shutil
            shutil.copy2(source_path, target_file)

            return {
                "success": True,
                "file_path": str(target_file),
                "filename": target_file.name,
                "folder": folder,
            }

        except Exception as e:
            logger.error(f"Error saving file to vault: {e}")
            return {"error": str(e)}

    def batch_save_to_vault(
        self,
        files: List[Dict[str, Any]],
        vault_path: Optional[str] = None,
        folder: str = "0-inbox",
        tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Save multiple files to the vault.

        Args:
            files: List of dicts with 'content' and 'filename' keys.
            vault_path: Override vault path.
            folder: Folder within vault.
            tags: Tags to apply to all files.

        Returns:
            Dict with results for each file.
        """
        results = {"success": [], "failed": []}

        for file_info in files:
            content = file_info.get("content")
            filename = file_info.get("filename")

            if not content or not filename:
                results["failed"].append({
                    "filename": filename,
                    "error": "Missing content or filename",
                })
                continue

            result = self.save_to_vault(
                content=content,
                filename=filename,
                vault_path=vault_path,
                folder=folder,
                tags=tags,
            )

            if result.get("success"):
                results["success"].append(result)
            else:
                results["failed"].append({
                    "filename": filename,
                    "error": result.get("error"),
                })

        return {
            "saved": len(results["success"]),
            "failed": len(results["failed"]),
            "results": results,
        }

    def doc_to_vault(
        self,
        file_path: Union[str, Path],
        vault_path: Optional[str] = None,
        folder: str = "0-inbox",
        tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Convert a document to markdown and save to vault.

        Supports DOCX, XLSX, PPTX, and PDF files.

        Args:
            file_path: Path to the document file.
            vault_path: Override vault path.
            folder: Folder within vault.
            tags: Additional tags.

        Returns:
            Dict with success status and file path.
        """
        from docs_mcp.processors.office import get_office_processor
        from docs_mcp.processors.pdf import get_pdf_processor

        source_path = Path(file_path)
        if not source_path.exists():
            return {"error": f"File not found: {file_path}"}

        ext = source_path.suffix.lower()

        # Convert based on file type
        if ext == ".docx":
            processor = get_office_processor()
            result = processor.docx_to_markdown(file_path)
        elif ext == ".xlsx":
            processor = get_office_processor()
            result = processor.xlsx_to_csv(file_path)  # CSV is more useful for vault
            if "csv" in result:
                result["markdown"] = f"```csv\n{result['csv']}\n```"
        elif ext == ".pptx":
            processor = get_office_processor()
            result = processor.pptx_to_markdown(file_path)
        elif ext == ".pdf":
            processor = get_pdf_processor()
            result = processor.pdf_to_markdown(file_path)
        else:
            return {"error": f"Unsupported file type: {ext}"}

        if "error" in result:
            return result

        markdown = result.get("markdown", "")
        if not markdown:
            return {"error": "Failed to extract content from document"}

        # Generate filename from source
        filename = f"{datetime.now().strftime('%Y-%m-%d')} {source_path.stem}"

        return self.save_to_vault(
            content=markdown,
            filename=filename,
            vault_path=vault_path,
            folder=folder,
            source="local",
            original_path=str(source_path),
            tags=tags,
            frontmatter_extra={"original_type": ext[1:]},  # Remove the dot
        )

    def ocr_to_vault(
        self,
        file_path: Union[str, Path],
        vault_path: Optional[str] = None,
        folder: str = "0-inbox",
        language: str = "eng",
        tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        OCR an image or PDF and save the text to vault.

        Args:
            file_path: Path to image or PDF file.
            vault_path: Override vault path.
            folder: Folder within vault.
            language: Tesseract language code.
            tags: Additional tags.

        Returns:
            Dict with success status and file path.
        """
        from docs_mcp.processors.ocr import get_ocr_processor

        source_path = Path(file_path)
        if not source_path.exists():
            return {"error": f"File not found: {file_path}"}

        processor = get_ocr_processor()
        result = processor.ocr_file(file_path, language=language)

        if "error" in result:
            return result

        text = result.get("text", "")
        if not text:
            return {"error": "OCR produced no text"}

        # Format as markdown
        confidence = result.get("confidence", 0)
        markdown = f"# OCR Result\n\n"
        markdown += f"**Source:** {source_path.name}\n"
        markdown += f"**Confidence:** {confidence}%\n"
        markdown += f"**Method:** {result.get('method', 'unknown')}\n\n"
        markdown += "---\n\n"
        markdown += text

        # Generate filename
        filename = f"{datetime.now().strftime('%Y-%m-%d')} OCR - {source_path.stem}"

        return self.save_to_vault(
            content=markdown,
            filename=filename,
            vault_path=vault_path,
            folder=folder,
            source="ocr",
            original_path=str(source_path),
            tags=tags,
            frontmatter_extra={
                "ocr_confidence": confidence,
                "ocr_method": result.get("method", "unknown"),
            },
        )


# Singleton instance
_processor: Optional[VaultProcessor] = None


def get_vault_processor() -> VaultProcessor:
    """Get the singleton VaultProcessor instance."""
    global _processor
    if _processor is None:
        _processor = VaultProcessor()
    return _processor
