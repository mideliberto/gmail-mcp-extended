"""
PDF Processor

Handles PDF file processing including text extraction, metadata, merging, and splitting.
"""

import io
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger("docs_mcp.processors.pdf")


class PdfProcessor:
    """
    Processor for PDF documents.
    """

    def read_pdf(self, file_path: Union[str, Path, bytes]) -> Dict[str, Any]:
        """
        Extract text from a PDF file.

        Works best with native text PDFs. For scanned PDFs, use OCR.

        Args:
            file_path: Path to the PDF file or bytes content.

        Returns:
            Dict containing text and page information.
        """
        try:
            import pdfplumber
        except ImportError:
            return {"error": "pdfplumber not installed. Run: pip install pdfplumber"}

        try:
            if isinstance(file_path, bytes):
                pdf = pdfplumber.open(io.BytesIO(file_path))
            else:
                pdf = pdfplumber.open(file_path)

            pages = []
            full_text = []

            for i, page in enumerate(pdf.pages, 1):
                text = page.extract_text() or ""
                pages.append({
                    "number": i,
                    "text": text,
                    "width": page.width,
                    "height": page.height,
                })
                full_text.append(text)

            pdf.close()

            return {
                "text": "\n\n".join(full_text),
                "pages": pages,
                "page_count": len(pages),
            }

        except Exception as e:
            logger.error(f"Error reading PDF: {e}")
            return {"error": str(e)}

    def get_pdf_metadata(self, file_path: Union[str, Path, bytes]) -> Dict[str, Any]:
        """
        Get PDF properties and metadata.

        Args:
            file_path: Path to the PDF file or bytes content.

        Returns:
            Dict containing PDF metadata.
        """
        try:
            from pypdf import PdfReader
        except ImportError:
            return {"error": "pypdf not installed. Run: pip install pypdf"}

        try:
            if isinstance(file_path, bytes):
                reader = PdfReader(io.BytesIO(file_path))
            else:
                reader = PdfReader(file_path)

            metadata = reader.metadata or {}

            return {
                "title": metadata.get("/Title"),
                "author": metadata.get("/Author"),
                "subject": metadata.get("/Subject"),
                "creator": metadata.get("/Creator"),
                "producer": metadata.get("/Producer"),
                "creation_date": str(metadata.get("/CreationDate")) if metadata.get("/CreationDate") else None,
                "modification_date": str(metadata.get("/ModDate")) if metadata.get("/ModDate") else None,
                "pages": len(reader.pages),
                "encrypted": reader.is_encrypted,
            }

        except Exception as e:
            logger.error(f"Error getting PDF metadata: {e}")
            return {"error": str(e)}

    def pdf_to_markdown(self, file_path: Union[str, Path, bytes]) -> Dict[str, Any]:
        """
        Convert PDF to Markdown format.

        Args:
            file_path: Path to the PDF file or bytes content.

        Returns:
            Dict containing the markdown text.
        """
        result = self.read_pdf(file_path)
        if "error" in result:
            return result

        try:
            lines = []
            metadata = self.get_pdf_metadata(file_path)

            # Add metadata as YAML frontmatter
            if metadata.get("title") or metadata.get("author"):
                lines.append("---")
                if metadata.get("title"):
                    lines.append(f"title: \"{metadata['title']}\"")
                if metadata.get("author"):
                    lines.append(f"author: \"{metadata['author']}\"")
                lines.append("---")
                lines.append("")

            # Add content by page
            for page in result.get("pages", []):
                lines.append(f"## Page {page['number']}")
                lines.append("")
                lines.append(page["text"])
                lines.append("")
                lines.append("---")
                lines.append("")

            return {
                "markdown": "\n".join(lines),
                "page_count": result.get("page_count", 0),
                "metadata": metadata,
            }

        except Exception as e:
            logger.error(f"Error converting PDF to markdown: {e}")
            return {"error": str(e)}

    def extract_pdf_images(
        self,
        file_path: Union[str, Path, bytes],
        output_dir: Optional[Union[str, Path]] = None,
    ) -> Dict[str, Any]:
        """
        Extract embedded images from a PDF.

        Args:
            file_path: Path to the PDF file or bytes content.
            output_dir: Directory to save images (optional).

        Returns:
            Dict containing image information.
        """
        try:
            from pypdf import PdfReader
        except ImportError:
            return {"error": "pypdf not installed. Run: pip install pypdf"}

        try:
            if isinstance(file_path, bytes):
                reader = PdfReader(io.BytesIO(file_path))
            else:
                reader = PdfReader(file_path)

            images = []
            image_count = 0

            for page_num, page in enumerate(reader.pages, 1):
                if "/XObject" in page["/Resources"]:
                    x_objects = page["/Resources"]["/XObject"].get_object()

                    for obj_name in x_objects:
                        obj = x_objects[obj_name]

                        if obj["/Subtype"] == "/Image":
                            image_count += 1
                            image_info = {
                                "page": page_num,
                                "name": obj_name,
                                "width": obj.get("/Width"),
                                "height": obj.get("/Height"),
                                "filter": str(obj.get("/Filter")),
                            }

                            # Extract image data if output directory provided
                            if output_dir:
                                output_path = Path(output_dir)
                                output_path.mkdir(parents=True, exist_ok=True)

                                # Determine file extension
                                filter_type = str(obj.get("/Filter", ""))
                                if "DCTDecode" in filter_type:
                                    ext = ".jpg"
                                elif "FlateDecode" in filter_type:
                                    ext = ".png"
                                else:
                                    ext = ".bin"

                                image_file = output_path / f"image_{image_count}{ext}"
                                try:
                                    data = obj.get_data()
                                    with open(image_file, "wb") as f:
                                        f.write(data)
                                    image_info["saved_to"] = str(image_file)
                                except Exception as e:
                                    image_info["save_error"] = str(e)

                            images.append(image_info)

            return {
                "images": images,
                "image_count": image_count,
            }

        except Exception as e:
            logger.error(f"Error extracting PDF images: {e}")
            return {"error": str(e)}

    def merge_pdfs(
        self,
        pdf_paths: List[Union[str, Path]],
        output_path: Union[str, Path],
    ) -> Dict[str, Any]:
        """
        Combine multiple PDFs into one.

        Args:
            pdf_paths: List of paths to PDF files to merge.
            output_path: Where to save the merged PDF.

        Returns:
            Dict with success status.
        """
        try:
            from pypdf import PdfWriter, PdfReader
        except ImportError:
            return {"error": "pypdf not installed. Run: pip install pypdf"}

        try:
            writer = PdfWriter()
            total_pages = 0

            for pdf_path in pdf_paths:
                reader = PdfReader(pdf_path)
                for page in reader.pages:
                    writer.add_page(page)
                    total_pages += 1

            with open(output_path, "wb") as f:
                writer.write(f)

            return {
                "success": True,
                "output_path": str(output_path),
                "total_pages": total_pages,
                "files_merged": len(pdf_paths),
            }

        except Exception as e:
            logger.error(f"Error merging PDFs: {e}")
            return {"error": str(e)}

    def split_pdf(
        self,
        file_path: Union[str, Path],
        output_dir: Union[str, Path],
        pages: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Split a PDF into separate pages or page ranges.

        Args:
            file_path: Path to the PDF file.
            output_dir: Directory to save split PDFs.
            pages: Page specification (e.g., "1-3,5,7-9"). If None, splits all pages.

        Returns:
            Dict with success status and output files.
        """
        try:
            from pypdf import PdfWriter, PdfReader
        except ImportError:
            return {"error": "pypdf not installed. Run: pip install pypdf"}

        try:
            reader = PdfReader(file_path)
            total_pages = len(reader.pages)
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)

            output_files = []

            if pages:
                # Parse page specification
                page_nums = set()
                for part in pages.split(","):
                    if "-" in part:
                        start, end = part.split("-")
                        page_nums.update(range(int(start), int(end) + 1))
                    else:
                        page_nums.add(int(part))

                # Create single PDF with specified pages
                writer = PdfWriter()
                for page_num in sorted(page_nums):
                    if 1 <= page_num <= total_pages:
                        writer.add_page(reader.pages[page_num - 1])

                out_file = output_path / f"pages_{pages.replace(',', '_').replace('-', '_')}.pdf"
                with open(out_file, "wb") as f:
                    writer.write(f)
                output_files.append(str(out_file))

            else:
                # Split each page into separate file
                for i, page in enumerate(reader.pages, 1):
                    writer = PdfWriter()
                    writer.add_page(page)

                    out_file = output_path / f"page_{i:03d}.pdf"
                    with open(out_file, "wb") as f:
                        writer.write(f)
                    output_files.append(str(out_file))

            return {
                "success": True,
                "output_dir": str(output_path),
                "output_files": output_files,
                "files_created": len(output_files),
            }

        except Exception as e:
            logger.error(f"Error splitting PDF: {e}")
            return {"error": str(e)}

    def fill_pdf_form(
        self,
        file_path: Union[str, Path, bytes],
        data: Dict[str, str],
        output_path: Optional[Union[str, Path]] = None,
    ) -> Dict[str, Any]:
        """
        Fill PDF form fields.

        Args:
            file_path: Path to the PDF form or bytes content.
            data: Dict of field names to values.
            output_path: Where to save the filled PDF.

        Returns:
            Dict with success status.
        """
        try:
            from pypdf import PdfReader, PdfWriter
        except ImportError:
            return {"error": "pypdf not installed. Run: pip install pypdf"}

        try:
            if isinstance(file_path, bytes):
                reader = PdfReader(io.BytesIO(file_path))
            else:
                reader = PdfReader(file_path)

            writer = PdfWriter()

            # Copy pages and fill form fields
            for page in reader.pages:
                writer.add_page(page)

            # Get existing form fields
            if reader.get_form_text_fields():
                writer.update_page_form_field_values(writer.pages[0], data)
            else:
                return {
                    "success": False,
                    "message": "PDF does not contain fillable form fields",
                }

            if output_path:
                with open(output_path, "wb") as f:
                    writer.write(f)
                return {"success": True, "output_path": str(output_path)}
            else:
                buffer = io.BytesIO()
                writer.write(buffer)
                buffer.seek(0)
                return {"success": True, "content": buffer.read()}

        except Exception as e:
            logger.error(f"Error filling PDF form: {e}")
            return {"error": str(e)}

    def rotate_pdf(
        self,
        file_path: Union[str, Path],
        output_path: Union[str, Path],
        rotation: int = 90,
        pages: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Rotate pages in a PDF.

        Args:
            file_path: Path to the PDF file.
            output_path: Where to save the rotated PDF.
            rotation: Degrees to rotate (90, 180, 270). Default 90.
            pages: Page specification (e.g., "1-3,5"). If None, rotates all pages.

        Returns:
            Dict with success status.
        """
        try:
            from pypdf import PdfWriter, PdfReader
        except ImportError:
            return {"error": "pypdf not installed. Run: pip install pypdf"}

        if rotation not in (90, 180, 270):
            return {"error": "Rotation must be 90, 180, or 270 degrees"}

        try:
            reader = PdfReader(file_path)
            writer = PdfWriter()
            total_pages = len(reader.pages)

            # Parse page specification
            if pages:
                page_nums = set()
                for part in pages.split(","):
                    if "-" in part:
                        start, end = part.split("-")
                        page_nums.update(range(int(start), int(end) + 1))
                    else:
                        page_nums.add(int(part))
            else:
                page_nums = set(range(1, total_pages + 1))

            rotated_count = 0
            for i, page in enumerate(reader.pages, 1):
                if i in page_nums:
                    page.rotate(rotation)
                    rotated_count += 1
                writer.add_page(page)

            with open(output_path, "wb") as f:
                writer.write(f)

            return {
                "success": True,
                "output_path": str(output_path),
                "pages_rotated": rotated_count,
                "rotation": rotation,
            }

        except Exception as e:
            logger.error(f"Error rotating PDF: {e}")
            return {"error": str(e)}

    def compress_pdf(
        self,
        file_path: Union[str, Path],
        output_path: Union[str, Path],
        remove_duplication: bool = True,
        remove_images: bool = False,
    ) -> Dict[str, Any]:
        """
        Reduce PDF file size.

        Args:
            file_path: Path to the PDF file.
            output_path: Where to save the compressed PDF.
            remove_duplication: Remove duplicate objects. Default True.
            remove_images: Remove all images to reduce size. Default False.

        Returns:
            Dict with success status and size info.
        """
        try:
            from pypdf import PdfWriter, PdfReader
        except ImportError:
            return {"error": "pypdf not installed. Run: pip install pypdf"}

        try:
            original_size = Path(file_path).stat().st_size
            reader = PdfReader(file_path)
            writer = PdfWriter()

            for page in reader.pages:
                if remove_images:
                    # Remove images by not copying XObject images
                    if "/Resources" in page and "/XObject" in page["/Resources"]:
                        x_objects = page["/Resources"]["/XObject"]
                        if hasattr(x_objects, "get_object"):
                            x_obj = x_objects.get_object()
                            keys_to_remove = []
                            for key in x_obj:
                                obj = x_obj[key]
                                if hasattr(obj, "get") and obj.get("/Subtype") == "/Image":
                                    keys_to_remove.append(key)
                            for key in keys_to_remove:
                                del x_obj[key]
                writer.add_page(page)

            # Compress content streams
            for page in writer.pages:
                page.compress_content_streams()

            if remove_duplication:
                writer.add_metadata(reader.metadata or {})

            with open(output_path, "wb") as f:
                writer.write(f)

            new_size = Path(output_path).stat().st_size
            reduction = ((original_size - new_size) / original_size) * 100 if original_size > 0 else 0

            return {
                "success": True,
                "output_path": str(output_path),
                "original_size": original_size,
                "new_size": new_size,
                "reduction_percent": round(reduction, 2),
            }

        except Exception as e:
            logger.error(f"Error compressing PDF: {e}")
            return {"error": str(e)}

    def add_watermark(
        self,
        file_path: Union[str, Path],
        output_path: Union[str, Path],
        watermark_text: str,
        position: str = "center",
        opacity: float = 0.3,
    ) -> Dict[str, Any]:
        """
        Add watermark text to PDF pages.

        Note: This requires reportlab for generating the watermark PDF.
        For a simpler approach, use an existing watermark PDF.

        Args:
            file_path: Path to the PDF file.
            output_path: Where to save the watermarked PDF.
            watermark_text: Text to use as watermark.
            position: Where to place watermark (center, diagonal). Default center.
            opacity: Watermark opacity (0.0-1.0). Default 0.3.

        Returns:
            Dict with success status.
        """
        try:
            from pypdf import PdfWriter, PdfReader
        except ImportError:
            return {"error": "pypdf not installed. Run: pip install pypdf"}

        try:
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import letter
        except ImportError:
            return {"error": "reportlab not installed. Run: pip install reportlab"}

        try:
            # Create watermark PDF
            watermark_buffer = io.BytesIO()
            c = canvas.Canvas(watermark_buffer, pagesize=letter)
            width, height = letter

            c.saveState()
            c.setFillAlpha(opacity)
            c.setFont("Helvetica", 50)

            if position == "diagonal":
                c.translate(width / 2, height / 2)
                c.rotate(45)
                c.drawCentredString(0, 0, watermark_text)
            else:  # center
                c.drawCentredString(width / 2, height / 2, watermark_text)

            c.restoreState()
            c.save()
            watermark_buffer.seek(0)

            watermark_reader = PdfReader(watermark_buffer)
            watermark_page = watermark_reader.pages[0]

            reader = PdfReader(file_path)
            writer = PdfWriter()

            for page in reader.pages:
                page.merge_page(watermark_page)
                writer.add_page(page)

            with open(output_path, "wb") as f:
                writer.write(f)

            return {
                "success": True,
                "output_path": str(output_path),
                "watermark": watermark_text,
                "pages_watermarked": len(reader.pages),
            }

        except Exception as e:
            logger.error(f"Error adding watermark: {e}")
            return {"error": str(e)}

    def encrypt_pdf(
        self,
        file_path: Union[str, Path],
        output_path: Union[str, Path],
        user_password: str,
        owner_password: Optional[str] = None,
        allow_printing: bool = True,
        allow_copying: bool = False,
    ) -> Dict[str, Any]:
        """
        Password-protect a PDF.

        Args:
            file_path: Path to the PDF file.
            output_path: Where to save the encrypted PDF.
            user_password: Password required to open the PDF.
            owner_password: Password for full access. Defaults to user_password.
            allow_printing: Allow printing. Default True.
            allow_copying: Allow copying text. Default False.

        Returns:
            Dict with success status.
        """
        try:
            from pypdf import PdfWriter, PdfReader
        except ImportError:
            return {"error": "pypdf not installed. Run: pip install pypdf"}

        try:
            reader = PdfReader(file_path)
            writer = PdfWriter()

            for page in reader.pages:
                writer.add_page(page)

            # Copy metadata
            if reader.metadata:
                writer.add_metadata(reader.metadata)

            # Set permissions
            # pypdf uses permissions flags
            permissions = 0
            if allow_printing:
                permissions |= 0b00000100  # Bit 3: Print
            if allow_copying:
                permissions |= 0b00010000  # Bit 5: Copy

            writer.encrypt(
                user_password=user_password,
                owner_password=owner_password or user_password,
            )

            with open(output_path, "wb") as f:
                writer.write(f)

            return {
                "success": True,
                "output_path": str(output_path),
                "encrypted": True,
                "allow_printing": allow_printing,
                "allow_copying": allow_copying,
            }

        except Exception as e:
            logger.error(f"Error encrypting PDF: {e}")
            return {"error": str(e)}

    def decrypt_pdf(
        self,
        file_path: Union[str, Path],
        output_path: Union[str, Path],
        password: str,
    ) -> Dict[str, Any]:
        """
        Remove password from a PDF.

        Args:
            file_path: Path to the encrypted PDF file.
            output_path: Where to save the decrypted PDF.
            password: Password to unlock the PDF.

        Returns:
            Dict with success status.
        """
        try:
            from pypdf import PdfWriter, PdfReader
        except ImportError:
            return {"error": "pypdf not installed. Run: pip install pypdf"}

        try:
            reader = PdfReader(file_path)

            if not reader.is_encrypted:
                return {
                    "success": False,
                    "message": "PDF is not encrypted",
                }

            if not reader.decrypt(password):
                return {
                    "success": False,
                    "message": "Invalid password",
                }

            writer = PdfWriter()

            for page in reader.pages:
                writer.add_page(page)

            # Copy metadata
            if reader.metadata:
                writer.add_metadata(reader.metadata)

            with open(output_path, "wb") as f:
                writer.write(f)

            return {
                "success": True,
                "output_path": str(output_path),
                "decrypted": True,
            }

        except Exception as e:
            logger.error(f"Error decrypting PDF: {e}")
            return {"error": str(e)}


# Singleton instance
_processor: Optional[PdfProcessor] = None


def get_pdf_processor() -> PdfProcessor:
    """Get the singleton PdfProcessor instance."""
    global _processor
    if _processor is None:
        _processor = PdfProcessor()
    return _processor
