"""Build the competition AI usage disclosure PDF from its Markdown source."""

from __future__ import annotations

import html
import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "reports" / "AI工具使用详情.md"
OUTPUT = ROOT / "reports" / "AI 工具使用详情.pdf"
REGULAR_FONT = Path(r"C:\Windows\Fonts\msyh.ttc")
BOLD_FONT = Path(r"C:\Windows\Fonts\msyhbd.ttc")


def register_fonts() -> None:
    """Register embedded Chinese fonts so the PDF is portable."""
    pdfmetrics.registerFont(TTFont("MicrosoftYaHei", str(REGULAR_FONT)))
    pdfmetrics.registerFont(TTFont("MicrosoftYaHei-Bold", str(BOLD_FONT)))
    pdfmetrics.registerFontFamily(
        "MicrosoftYaHei",
        normal="MicrosoftYaHei",
        bold="MicrosoftYaHei-Bold",
    )


def inline_markup(text: str) -> str:
    """Convert the small inline Markdown subset used by the report."""
    escaped = html.escape(text.strip())
    escaped = re.sub(r"`([^`]+)`", r'<font name="MicrosoftYaHei">\1</font>', escaped)
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", escaped)
    return escaped


def make_styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    common = {
        "fontName": "MicrosoftYaHei",
        "textColor": colors.HexColor("#20242A"),
        "wordWrap": "CJK",
    }
    return {
        "title": ParagraphStyle(
            "ChineseTitle",
            parent=base["Title"],
            fontName="MicrosoftYaHei-Bold",
            fontSize=20,
            leading=28,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#18324A"),
            spaceAfter=12 * mm,
        ),
        "h2": ParagraphStyle(
            "Heading2Chinese",
            parent=base["Heading2"],
            fontName="MicrosoftYaHei-Bold",
            fontSize=14,
            leading=20,
            textColor=colors.HexColor("#18324A"),
            spaceBefore=7 * mm,
            spaceAfter=3 * mm,
            keepWithNext=True,
        ),
        "h3": ParagraphStyle(
            "Heading3Chinese",
            parent=base["Heading3"],
            fontName="MicrosoftYaHei-Bold",
            fontSize=11.5,
            leading=17,
            textColor=colors.HexColor("#315A72"),
            spaceBefore=4 * mm,
            spaceAfter=2 * mm,
            keepWithNext=True,
        ),
        "body": ParagraphStyle(
            "BodyChinese",
            parent=base["BodyText"],
            fontSize=10.2,
            leading=17,
            firstLineIndent=2 * 10.2,
            alignment=TA_JUSTIFY,
            spaceAfter=2.2 * mm,
            **common,
        ),
        "label": ParagraphStyle(
            "LabelChinese",
            parent=base["BodyText"],
            fontSize=10.2,
            leading=17,
            alignment=TA_JUSTIFY,
            spaceAfter=2 * mm,
            **common,
        ),
        "quote": ParagraphStyle(
            "QuoteChinese",
            parent=base["BodyText"],
            fontSize=10,
            leading=17,
            leftIndent=6 * mm,
            rightIndent=4 * mm,
            borderColor=colors.HexColor("#6F91A6"),
            borderWidth=1.5,
            borderPadding=(2 * mm, 3 * mm, 2 * mm, 4 * mm),
            backColor=colors.HexColor("#F3F7F9"),
            spaceBefore=2 * mm,
            spaceAfter=3 * mm,
            **common,
        ),
        "bullet": ParagraphStyle(
            "BulletChinese",
            parent=base["BodyText"],
            fontSize=10.2,
            leading=17,
            leftIndent=7 * mm,
            firstLineIndent=-4 * mm,
            spaceAfter=1.5 * mm,
            **common,
        ),
        "table": ParagraphStyle(
            "TableChinese",
            parent=base["BodyText"],
            fontSize=8.2,
            leading=12,
            **common,
        ),
        "table_header": ParagraphStyle(
            "TableHeaderChinese",
            parent=base["BodyText"],
            fontName="MicrosoftYaHei-Bold",
            fontSize=8.4,
            leading=12,
            textColor=colors.white,
            wordWrap="CJK",
        ),
    }


def parse_table(lines: list[str], styles: dict[str, ParagraphStyle]) -> Table:
    rows = [[cell.strip() for cell in line.strip().strip("|").split("|")] for line in lines]
    rows.pop(1)
    rendered = []
    for row_index, row in enumerate(rows):
        style = styles["table_header"] if row_index == 0 else styles["table"]
        rendered.append([Paragraph(inline_markup(cell), style) for cell in row])

    width = A4[0] - 40 * mm
    column_count = len(rendered[0])
    if column_count == 4:
        widths = [0.10 * width, 0.19 * width, 0.29 * width, 0.42 * width]
    elif column_count == 3:
        widths = [0.20 * width, 0.35 * width, 0.45 * width]
    else:
        widths = [width / column_count] * column_count

    table = Table(rendered, colWidths=widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#315A72")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#AAB7C0")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F7F8")]),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return table


def markdown_to_story(text: str, styles: dict[str, ParagraphStyle]) -> list:
    story: list = []
    lines = text.splitlines()
    index = 0
    while index < len(lines):
        line = lines[index].rstrip()
        if not line or line.strip() == "---":
            index += 1
            continue
        if line.startswith("# "):
            story.append(Paragraph(inline_markup(line[2:]), styles["title"]))
        elif line.startswith("## "):
            story.append(Paragraph(inline_markup(line[3:]), styles["h2"]))
        elif line.startswith("### "):
            story.append(Paragraph(inline_markup(line[4:]), styles["h3"]))
        elif line.startswith("|") and index + 1 < len(lines) and re.match(r"^\|[\s:|-]+\|$", lines[index + 1]):
            table_lines = [line, lines[index + 1]]
            index += 2
            while index < len(lines) and lines[index].startswith("|"):
                table_lines.append(lines[index])
                index += 1
            story.append(parse_table(table_lines, styles))
            story.append(Spacer(1, 3 * mm))
            continue
        elif line.startswith("> "):
            quote_lines = [line[2:].strip()]
            index += 1
            while index < len(lines) and lines[index].startswith("> "):
                quote_lines.append(lines[index][2:].strip())
                index += 1
            story.append(Paragraph(inline_markup(" ".join(quote_lines)), styles["quote"]))
            continue
        elif re.match(r"^- ", line):
            story.append(Paragraph("• " + inline_markup(line[2:]), styles["bullet"]))
        elif re.match(r"^\d+\. ", line):
            match = re.match(r"^(\d+)\.\s+(.*)$", line)
            assert match is not None
            story.append(Paragraph(f"{match.group(1)}. " + inline_markup(match.group(2)), styles["bullet"]))
        else:
            style = styles["label"] if line.startswith("**") else styles["body"]
            story.append(Paragraph(inline_markup(line), style))
        index += 1
    return story


def draw_page(canvas, document) -> None:
    canvas.saveState()
    canvas.setFont("MicrosoftYaHei", 8)
    canvas.setFillColor(colors.HexColor("#68747D"))
    canvas.drawString(20 * mm, A4[1] - 13 * mm, "“策联杯”数学建模竞赛支撑材料")
    canvas.drawRightString(A4[0] - 20 * mm, 12 * mm, f"第 {document.page} 页")
    canvas.setStrokeColor(colors.HexColor("#D4DBDF"))
    canvas.line(20 * mm, A4[1] - 15 * mm, A4[0] - 20 * mm, A4[1] - 15 * mm)
    canvas.restoreState()


def build() -> None:
    register_fonts()
    styles = make_styles()
    document = BaseDocTemplate(
        str(OUTPUT),
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=22 * mm,
        bottomMargin=20 * mm,
        title="AI 工具使用详情",
        author="参赛队",
    )
    frame = Frame(
        document.leftMargin,
        document.bottomMargin,
        document.width,
        document.height,
        id="content",
    )
    document.addPageTemplates(PageTemplate(id="main", frames=[frame], onPage=draw_page))
    story = markdown_to_story(SOURCE.read_text(encoding="utf-8"), styles)
    document.build(story)


if __name__ == "__main__":
    build()
