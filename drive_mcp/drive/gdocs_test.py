"""
Google Docs Test Request Generator

Generates batchUpdate requests for testing the gdocs builder.
This is a Python implementation matching the TypeScript gdocs-builder.ts output.
"""

from typing import Any, Dict, List


def hex_to_rgb(hex_color: str) -> Dict[str, float]:
    """Convert hex color to Google Docs RGB format."""
    clean = hex_color.lstrip("#")
    return {
        "red": int(clean[0:2], 16) / 255,
        "green": int(clean[2:4], 16) / 255,
        "blue": int(clean[4:6], 16) / 255,
    }


# Colors matching docgen styles
COLORS = {
    "primary_dark": "1F4E79",
    "border": "CCCCCC",
    "header_cell": "D9D9D9",
    "info_border": "1F4E79",
    "info_text": "1F4E79",
}


class GDocsTestBuilder:
    """Simple builder for generating test requests."""

    def __init__(self):
        self.requests: List[Dict[str, Any]] = []
        self.index: int = 1  # Google Docs starts at index 1

    def insert_text(self, text: str) -> tuple:
        """Insert text and return (start, end) indices."""
        start = self.index
        self.requests.append({
            "insertText": {
                "location": {"index": start},
                "text": text,
            }
        })
        self.index += len(text)
        return start, self.index

    def apply_paragraph_style(self, start: int, end: int, style: dict, fields: str):
        """Apply paragraph style to range."""
        self.requests.append({
            "updateParagraphStyle": {
                "range": {"startIndex": start, "endIndex": end},
                "paragraphStyle": style,
                "fields": fields,
            }
        })

    def apply_text_style(self, start: int, end: int, style: dict, fields: str):
        """Apply text style to range."""
        self.requests.append({
            "updateTextStyle": {
                "range": {"startIndex": start, "endIndex": end},
                "textStyle": style,
                "fields": fields,
            }
        })

    def insert_heading(self, text: str, level: int = 1):
        """Insert a heading."""
        start, end = self.insert_text(text + "\n")

        # Paragraph style
        self.apply_paragraph_style(
            start, end,
            {"namedStyleType": f"HEADING_{level}"},
            "namedStyleType"
        )

        # Text style (color + bold, exclude newline)
        self.apply_text_style(
            start, end - 1,
            {
                "foregroundColor": {"color": {"rgbColor": hex_to_rgb(COLORS["primary_dark"])}},
                "bold": True,
            },
            "foregroundColor,bold"
        )

    def insert_paragraph(self, text: str):
        """Insert a plain paragraph."""
        self.insert_text(text + "\n")

    def insert_formatted_paragraph(self, runs: List[Dict[str, Any]]):
        """Insert paragraph with mixed formatting."""
        for run in runs:
            text = run["text"]
            start, end = self.insert_text(text)

            style = run.get("style", {})
            if style:
                text_style = {}
                fields = []

                if style.get("bold"):
                    text_style["bold"] = True
                    fields.append("bold")
                if style.get("italic"):
                    text_style["italic"] = True
                    fields.append("italic")

                if fields:
                    self.apply_text_style(start, end, text_style, ",".join(fields))

        # Add newline
        self.insert_text("\n")

    def insert_bullet_list(self, items: List[Dict[str, Any]]):
        """Insert bullet list."""
        list_start = self.index

        for item in items:
            level = item.get("level", 0)
            prefix = "\t" * level
            self.insert_text(prefix + item["text"] + "\n")

        list_end = self.index

        self.requests.append({
            "createParagraphBullets": {
                "range": {"startIndex": list_start, "endIndex": list_end},
                "bulletPreset": "BULLET_DISC_CIRCLE_SQUARE",
            }
        })

    def insert_table(self, headers: List[str], rows: List[List[str]]):
        """Insert a simple table."""
        num_cols = len(headers)
        num_rows = len(rows) + 1
        table_start = self.index

        # Insert table structure
        self.requests.append({
            "insertTable": {
                "rows": num_rows,
                "columns": num_cols,
                "location": {"index": table_start},
            }
        })

        # Table structure size
        structure_size = 3 + num_rows * (num_cols * 2 + 1)

        # Build cell data
        all_rows = [headers] + rows
        cell_data = []

        for r, row in enumerate(all_rows):
            for c, text in enumerate(row):
                if text:
                    cell_data.append({
                        "row": r,
                        "col": c,
                        "text": text,
                        "is_header": r == 0,
                    })

        # Generate cell insert requests (will be reversed)
        cell_inserts = []
        cell_formats = []

        for i, cell in enumerate(cell_data):
            base_index = table_start + 4 + cell["row"] * (num_cols * 2 + 1) + cell["col"] * 2

            cell_inserts.append({
                "insertText": {
                    "location": {"index": base_index},
                    "text": cell["text"],
                }
            })

            # Format index accounts for prior content
            prior_content = sum(len(c["text"]) for c in cell_data[:i])
            format_index = base_index + prior_content

            # Header bold
            if cell["is_header"]:
                cell_formats.append({
                    "updateTextStyle": {
                        "range": {
                            "startIndex": format_index,
                            "endIndex": format_index + len(cell["text"]),
                        },
                        "textStyle": {"bold": True},
                        "fields": "bold",
                    }
                })

        # Add reversed cell inserts
        self.requests.extend(reversed(cell_inserts))
        self.requests.extend(cell_formats)

        # Header background
        self.requests.append({
            "updateTableCellStyle": {
                "tableRange": {
                    "tableCellLocation": {
                        "tableStartLocation": {"index": table_start},
                        "rowIndex": 0,
                        "columnIndex": 0,
                    },
                    "rowSpan": 1,
                    "columnSpan": num_cols,
                },
                "tableCellStyle": {
                    "backgroundColor": {"color": {"rgbColor": hex_to_rgb(COLORS["header_cell"])}},
                },
                "fields": "backgroundColor",
            }
        })

        # Borders for all cells
        border = {
            "color": {"color": {"rgbColor": hex_to_rgb(COLORS["border"])}},
            "width": {"magnitude": 0.5, "unit": "PT"},
            "dashStyle": "SOLID",
        }

        self.requests.append({
            "updateTableCellStyle": {
                "tableRange": {
                    "tableCellLocation": {
                        "tableStartLocation": {"index": table_start},
                        "rowIndex": 0,
                        "columnIndex": 0,
                    },
                    "rowSpan": num_rows,
                    "columnSpan": num_cols,
                },
                "tableCellStyle": {
                    "borderLeft": border,
                    "borderRight": border,
                    "borderTop": border,
                    "borderBottom": border,
                    "paddingTop": {"magnitude": 6, "unit": "PT"},
                    "paddingBottom": {"magnitude": 6, "unit": "PT"},
                    "paddingLeft": {"magnitude": 8, "unit": "PT"},
                    "paddingRight": {"magnitude": 8, "unit": "PT"},
                },
                "fields": "borderLeft,borderRight,borderTop,borderBottom,paddingTop,paddingBottom,paddingLeft,paddingRight",
            }
        })

        # Update index
        total_content = sum(len(c["text"]) for c in cell_data)
        self.index = table_start + structure_size + total_content

        # Newline after table
        self.insert_text("\n")

    def insert_callout(self, content: str, style: str = "info"):
        """Insert a callout box."""
        start, end = self.insert_text(content + "\n")

        # Left border + indent
        self.apply_paragraph_style(
            start, end,
            {
                "indentStart": {"magnitude": 36, "unit": "PT"},
                "indentEnd": {"magnitude": 36, "unit": "PT"},
                "borderLeft": {
                    "color": {"color": {"rgbColor": hex_to_rgb(COLORS["info_border"])}},
                    "width": {"magnitude": 3, "unit": "PT"},
                    "padding": {"magnitude": 12, "unit": "PT"},
                    "dashStyle": "SOLID",
                },
            },
            "indentStart,indentEnd,borderLeft"
        )

        # Text color
        self.apply_text_style(
            start, end - 1,
            {"foregroundColor": {"color": {"rgbColor": hex_to_rgb(COLORS["info_text"])}}},
            "foregroundColor"
        )

    def insert_document_style(self):
        """Add document-level styling (call at end)."""
        self.requests.insert(0, {
            "updateDocumentStyle": {
                "documentStyle": {
                    "marginTop": {"magnitude": 72, "unit": "PT"},
                    "marginBottom": {"magnitude": 72, "unit": "PT"},
                    "marginLeft": {"magnitude": 72, "unit": "PT"},
                    "marginRight": {"magnitude": 72, "unit": "PT"},
                },
                "fields": "marginTop,marginBottom,marginLeft,marginRight",
            }
        })

    def get_requests(self) -> List[Dict[str, Any]]:
        """Get all accumulated requests."""
        return self.requests


def generate_test_requests(test_type: str = "foundation") -> List[Dict[str, Any]]:
    """
    Generate test requests for the specified test type.

    Args:
        test_type: "foundation", "table", or "full"

    Returns:
        List of batchUpdate requests
    """
    if test_type == "foundation":
        return _generate_foundation_test()
    elif test_type == "table":
        return _generate_table_test()
    elif test_type == "full":
        return _generate_full_test()
    else:
        raise ValueError(f"Unknown test_type: {test_type}. Use 'foundation', 'table', or 'full'.")


def _generate_foundation_test() -> List[Dict[str, Any]]:
    """Generate foundation test: heading, paragraph, list, table, callout."""
    builder = GDocsTestBuilder()

    # 1. Heading
    builder.insert_heading("Foundation Test Document", 1)

    # 2. Paragraph with bold and italic
    builder.insert_formatted_paragraph([
        {"text": "This paragraph contains "},
        {"text": "bold text", "style": {"bold": True}},
        {"text": ", "},
        {"text": "italic text", "style": {"italic": True}},
        {"text": ", and "},
        {"text": "bold italic text", "style": {"bold": True, "italic": True}},
        {"text": "."},
    ])

    # 3. Bullet list with nesting
    builder.insert_heading("Key Points", 2)
    builder.insert_bullet_list([
        {"text": "First bullet point", "level": 0},
        {"text": "Nested bullet point", "level": 1},
        {"text": "Second top-level point", "level": 0},
        {"text": "Third top-level point", "level": 0},
    ])

    # 4. Simple table
    builder.insert_heading("Data Table", 2)
    builder.insert_table(
        ["Column A", "Column B", "Column C"],
        [
            ["Row 1 A", "Row 1 B", "Row 1 C"],
            ["Row 2 A", "Row 2 B", "Row 2 C"],
        ]
    )

    # 5. Callout
    builder.insert_callout(
        "This is an important informational callout to verify styling.",
        "info"
    )

    builder.insert_document_style()
    return builder.get_requests()


def _generate_table_test() -> List[Dict[str, Any]]:
    """Generate focused table test."""
    builder = GDocsTestBuilder()

    builder.insert_heading("Table Test", 1)

    builder.insert_paragraph("Testing table rendering:")

    builder.insert_table(
        ["Header 1", "Header 2", "Header 3", "Header 4"],
        [
            ["A1", "B1", "C1", "D1"],
            ["A2", "B2", "C2", "D2"],
            ["A3", "B3", "C3", "D3"],
        ]
    )

    builder.insert_paragraph("Table should have:")
    builder.insert_bullet_list([
        {"text": "Bold header row", "level": 0},
        {"text": "Gray header background", "level": 0},
        {"text": "Borders on all cells", "level": 0},
        {"text": "Proper cell padding", "level": 0},
    ])

    builder.insert_document_style()
    return builder.get_requests()


def _generate_full_test() -> List[Dict[str, Any]]:
    """Generate comprehensive test of all features."""
    builder = GDocsTestBuilder()

    builder.insert_heading("Comprehensive Test Document", 1)

    builder.insert_paragraph("This document tests all major formatting features.")

    # Headings
    builder.insert_heading("Heading Level 2", 2)
    builder.insert_heading("Heading Level 3", 3)

    # Formatted text
    builder.insert_heading("Text Formatting", 2)
    builder.insert_formatted_paragraph([
        {"text": "Normal, "},
        {"text": "bold", "style": {"bold": True}},
        {"text": ", "},
        {"text": "italic", "style": {"italic": True}},
        {"text": ", "},
        {"text": "bold+italic", "style": {"bold": True, "italic": True}},
        {"text": "."},
    ])

    # Lists
    builder.insert_heading("Lists", 2)
    builder.insert_bullet_list([
        {"text": "Level 0 item", "level": 0},
        {"text": "Level 1 nested", "level": 1},
        {"text": "Level 2 deep", "level": 2},
        {"text": "Back to level 0", "level": 0},
    ])

    # Table
    builder.insert_heading("Table", 2)
    builder.insert_table(
        ["Name", "Value", "Status"],
        [
            ["Item 1", "100", "Active"],
            ["Item 2", "200", "Pending"],
        ]
    )

    # Callout
    builder.insert_heading("Callout", 2)
    builder.insert_callout("This is a callout box with important information.", "info")

    builder.insert_document_style()
    return builder.get_requests()
