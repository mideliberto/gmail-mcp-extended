# docs-mcp Tool Reference

Local document processing server with 27 tools. **No Google authentication required.**

## Prerequisites

### Python Dependencies

```bash
# Office documents (DOCX, XLSX, PPTX)
pip install python-docx openpyxl python-pptx

# PDF processing
pip install pypdf pdfplumber

# Local OCR (optional)
pip install pytesseract pdf2image Pillow
```

### System Dependencies (for OCR)

**macOS:**
```bash
brew install tesseract poppler
```

**Ubuntu/Debian:**
```bash
sudo apt install tesseract-ocr poppler-utils

# Additional languages (optional)
sudo apt install tesseract-ocr-fra tesseract-ocr-deu tesseract-ocr-spa
```

**Windows:**
- Tesseract: https://github.com/UB-Mannheim/tesseract/wiki
- Poppler: https://github.com/osber/poppler-windows/releases
- Add both to system PATH

---

## Office Reading (3 tools)

| Tool | Description | Parameters |
|------|-------------|------------|
| `read_docx_content` | Extract text, tables, structure | `file_path`, `include_tables`, `include_headers` |
| `read_xlsx_content` | Read spreadsheet data | `file_path`, `sheet_name`, `include_formulas` |
| `read_pptx_content` | Extract slides and notes | `file_path`, `include_notes`, `include_images` |

### DOCX Output Structure

```python
{
    "paragraphs": ["paragraph 1", "paragraph 2", ...],
    "tables": [
        {
            "rows": [["cell1", "cell2"], ["cell3", "cell4"]]
        }
    ],
    "headers": ["Header 1", "Header 2"],
    "metadata": {
        "author": "...",
        "created": "...",
        "modified": "..."
    }
}
```

### XLSX Output Structure

```python
{
    "sheets": ["Sheet1", "Sheet2"],
    "data": {
        "Sheet1": {
            "A1": "value",
            "B1": "=SUM(A1:A10)",  # if include_formulas=True
            ...
        }
    },
    "metadata": {...}
}
```

### PPTX Output Structure

```python
{
    "slides": [
        {
            "slide_number": 1,
            "title": "Slide Title",
            "content": ["bullet 1", "bullet 2"],
            "notes": "Speaker notes here"  # if include_notes=True
        }
    ],
    "metadata": {...}
}
```

---

## Office Templates (6 tools)

Use `{{variable_name}}` placeholders in documents.

| Tool | Description | Parameters |
|------|-------------|------------|
| `fill_docx_template` | Fill DOCX placeholders | `template_path`, `output_path`, `data` |
| `fill_xlsx_template` | Fill XLSX placeholders | `template_path`, `output_path`, `data` |
| `fill_pptx_template` | Fill PPTX placeholders | `template_path`, `output_path`, `data` |
| `create_docx_from_template` | Create new DOCX from template | `template_path`, `output_path`, `data` |
| `create_xlsx_from_template` | Create new XLSX from template | `template_path`, `output_path`, `data` |
| `create_pptx_from_template` | Create new PPTX from template | `template_path`, `output_path`, `data` |

### Template Example

**Template (invoice_template.docx):**
```
Invoice #{{invoice_number}}
Date: {{date}}
Client: {{client_name}}
Amount: ${{amount}}
```

**Usage:**
```python
fill_docx_template(
    template_path="/templates/invoice_template.docx",
    output_path="/output/invoice_001.docx",
    data={
        "invoice_number": "001",
        "date": "2026-01-22",
        "client_name": "Acme Corp",
        "amount": "1,500.00"
    }
)
```

---

## Office Export (3 tools)

| Tool | Description | Parameters |
|------|-------------|------------|
| `docx_to_markdown` | Convert DOCX to markdown | `file_path`, `output_path` |
| `xlsx_to_csv` | Convert XLSX to CSV | `file_path`, `output_path`, `sheet_name` |
| `pptx_to_markdown` | Convert PPTX to markdown | `file_path`, `output_path`, `include_notes` |

### Markdown Output Example

**DOCX → Markdown:**
```markdown
# Heading 1

Paragraph text here.

## Heading 2

- Bullet point 1
- Bullet point 2

| Column 1 | Column 2 |
|----------|----------|
| Cell 1   | Cell 2   |
```

**PPTX → Markdown:**
```markdown
# Slide 1: Introduction

- Point 1
- Point 2

> Speaker notes: Remember to mention...

---

# Slide 2: Details

...
```

---

## PDF Processing (7 tools)

| Tool | Description | Parameters |
|------|-------------|------------|
| `read_pdf_content` | Extract text from PDF | `file_path`, `pages` |
| `get_pdf_metadata` | Get PDF properties | `file_path` |
| `pdf_to_markdown` | Convert PDF to markdown | `file_path`, `output_path` |
| `extract_pdf_images` | Extract embedded images | `file_path`, `output_folder` |
| `merge_pdfs` | Combine multiple PDFs | `input_paths`, `output_path` |
| `split_pdf` | Split into pages/ranges | `file_path`, `output_folder`, `pages` |
| `fill_pdf_form` | Fill PDF form fields | `file_path`, `output_path`, `field_data` |

### Page Selection

```python
# All pages
read_pdf_content(file_path="doc.pdf")

# Specific pages
read_pdf_content(file_path="doc.pdf", pages=[1, 3, 5])

# Page range
read_pdf_content(file_path="doc.pdf", pages="1-5")
```

### Merge PDFs

```python
merge_pdfs(
    input_paths=["/path/to/doc1.pdf", "/path/to/doc2.pdf", "/path/to/doc3.pdf"],
    output_path="/path/to/merged.pdf"
)
```

### Split PDF

```python
# Split all pages into separate files
split_pdf(
    file_path="/path/to/document.pdf",
    output_folder="/path/to/pages/"
)
# Creates: page_001.pdf, page_002.pdf, ...

# Split specific pages
split_pdf(
    file_path="/path/to/document.pdf",
    output_folder="/path/to/pages/",
    pages=[1, 5, 10]
)
```

### Fill PDF Form

```python
fill_pdf_form(
    file_path="/forms/application.pdf",
    output_path="/completed/application_filled.pdf",
    field_data={
        "name": "John Doe",
        "email": "john@example.com",
        "date": "2026-01-22",
        "signature": "John Doe"
    }
)
```

---

## Local OCR (4 tools)

Uses Tesseract for offline OCR processing.

| Tool | Description | Parameters |
|------|-------------|------------|
| `ocr_image_local` | OCR image file | `file_path`, `language` |
| `ocr_pdf_local` | OCR scanned PDF | `file_path`, `language`, `pages` |
| `ocr_file` | Auto-detect and OCR | `file_path`, `language` |
| `ocr_to_vault` | OCR and save to vault | `file_path`, `vault_path`, `filename`, `language`, `tags` |

### Supported Image Formats

- PNG, JPG/JPEG, TIFF, BMP, GIF, WebP

### Language Codes

| Code | Language |
|------|----------|
| `eng` | English (default) |
| `fra` | French |
| `deu` | German |
| `spa` | Spanish |
| `ita` | Italian |
| `por` | Portuguese |
| `chi_sim` | Chinese (Simplified) |
| `chi_tra` | Chinese (Traditional) |
| `jpn` | Japanese |
| `kor` | Korean |

### Multi-language OCR

```python
# OCR with multiple languages
ocr_image_local(
    file_path="/scans/mixed_document.png",
    language="eng+fra+deu"  # English, French, German
)
```

### OCR Pipeline

```python
# 1. OCR a scanned document
result = ocr_pdf_local(
    file_path="/scans/old_document.pdf",
    language="eng"
)
# result["text"] contains extracted text
# result["pages"] contains per-page text

# 2. Save to vault with metadata
ocr_to_vault(
    file_path="/scans/receipt.jpg",
    vault_path="/Users/me/vault",
    filename="Receipt 2026-01-22",
    tags=["receipt", "expense"]
)
```

---

## Vault Integration (4 tools)

Save processed content to an Obsidian vault or similar note system.

| Tool | Description | Parameters |
|------|-------------|------------|
| `save_text_to_vault` | Save text as markdown | `text`, `vault_path`, `filename`, `folder`, `tags` |
| `save_file_to_vault` | Copy file to vault | `file_path`, `vault_path`, `folder` |
| `batch_save_to_vault` | Save multiple files | `file_paths`, `vault_path`, `folder` |
| `doc_to_vault` | Convert doc to markdown and save | `file_path`, `vault_path`, `filename`, `tags` |

### Vault Structure

Files are saved with frontmatter:

```markdown
---
type: document
source: /path/to/original.docx
created: 2026-01-22
tags:
  - imported
  - work
---

# Document Title

Content here...
```

### Examples

```python
# Save text content
save_text_to_vault(
    text="Meeting notes from today...",
    vault_path="/Users/me/ObsidianVault",
    filename="Meeting Notes 2026-01-22",
    folder="Meetings",
    tags=["meeting", "work"]
)

# Convert and save DOCX
doc_to_vault(
    file_path="/documents/report.docx",
    vault_path="/Users/me/ObsidianVault",
    filename="Q1 Report",
    tags=["report", "quarterly"]
)

# Batch import
batch_save_to_vault(
    file_paths=["/docs/a.pdf", "/docs/b.pdf", "/docs/c.pdf"],
    vault_path="/Users/me/ObsidianVault",
    folder="Imports/PDFs"
)
```

---

## Common Workflows

### Document Conversion Pipeline

```python
# 1. Read DOCX
content = read_docx_content("/documents/report.docx")

# 2. Convert to markdown
docx_to_markdown(
    file_path="/documents/report.docx",
    output_path="/output/report.md"
)

# 3. Save to vault
doc_to_vault(
    file_path="/documents/report.docx",
    vault_path="/vault",
    filename="Report"
)
```

### Invoice Generation

```python
# Generate from template
fill_docx_template(
    template_path="/templates/invoice.docx",
    output_path="/invoices/INV-001.docx",
    data={
        "invoice_number": "INV-001",
        "client": "Acme Corp",
        "items": "Consulting services",
        "amount": "5,000.00"
    }
)
```

### Scanned Document Processing

```python
# 1. OCR the scanned document
text = ocr_pdf_local(
    file_path="/scans/contract.pdf",
    language="eng"
)

# 2. Save to vault with tags
ocr_to_vault(
    file_path="/scans/contract.pdf",
    vault_path="/vault",
    filename="Contract - Acme Corp",
    tags=["contract", "legal", "acme"]
)
```

### PDF Manipulation

```python
# Merge multiple reports
merge_pdfs(
    input_paths=[
        "/reports/january.pdf",
        "/reports/february.pdf",
        "/reports/march.pdf"
    ],
    output_path="/reports/Q1_combined.pdf"
)

# Extract specific pages
split_pdf(
    file_path="/documents/large_doc.pdf",
    output_folder="/extracts/",
    pages=[1, 5, 10]  # Extract only these pages
)
```

---

## Environment Variables

| Variable | Description |
|----------|-------------|
| `VAULT_PATH` | Default vault path for vault tools |
| `TESSERACT_CMD` | Custom Tesseract binary path (optional) |

---

## Notes

- docs-mcp requires no Google authentication
- All processing happens locally
- OCR quality depends on image quality and Tesseract training data
- Large PDFs may take time to process
- Template placeholders use `{{variable}}` syntax
- Vault integration creates markdown with YAML frontmatter
