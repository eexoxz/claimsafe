from __future__ import annotations

import argparse
import html
import os
import subprocess
import sys
import json
import re
import shutil
from pathlib import Path

from reportlab.graphics import renderSVG
from reportlab.graphics.shapes import Drawing, Line, Polygon, Rect, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Flowable, Image, KeepTogether, PageBreak, Paragraph, Preformatted,
    SimpleDocTemplate, Spacer, Table, TableStyle,
)

REPO = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description="Build the ClaimSafe report from its versioned Markdown source.")
parser.add_argument("--output-dir", type=Path, default=REPO / ".local" / "report")
parser.add_argument("--single-pass", action="store_true", help=argparse.SUPPRESS)
args = parser.parse_args()
OUTPUT_DIR = args.output_dir.resolve()
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
SOURCE = REPO / "docs" / "REPORT_DRAFT.md"
ASSETS = REPO / "docs" / "report-assets"
OUTPUT = OUTPUT_DIR / "ClaimSafe_Report_Draft.pdf"
ASSETS.mkdir(parents=True, exist_ok=True)

font_directory = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
font_files = ["arial.ttf", "arialbd.ttf", "ariali.ttf", "arialbi.ttf"]
if not (font_directory / font_files[0]).exists():
    import reportlab
    font_directory = Path(reportlab.__file__).parent / "fonts"
    font_files = ["Vera.ttf", "VeraBd.ttf", "VeraIt.ttf", "VeraBI.ttf"]
for name, filename in zip(["Arial", "Arial-Bold", "Arial-Italic", "Arial-BoldItalic"], font_files):
    pdfmetrics.registerFont(TTFont(name, str(font_directory / filename)))
pdfmetrics.registerFontFamily("Arial", normal="Arial", bold="Arial-Bold", italic="Arial-Italic", boldItalic="Arial-BoldItalic")
FONT = "Arial"
INK = colors.HexColor("#171717")
GREY = colors.HexColor("#606060")
BORDER = colors.HexColor("#d9d9d9")
PAGE_W, PAGE_H = A4
WIDTH = PAGE_W - 112

styles = getSampleStyleSheet()
styles.add(ParagraphStyle("ReportBody", fontName=FONT, fontSize=10.5, leading=16,
                          textColor=INK, spaceAfter=9, allowWidows=0, allowOrphans=0))
styles.add(ParagraphStyle("ReportTitle", fontName="Arial-Bold", fontSize=26, leading=33,
                          textColor=colors.black, spaceAfter=20))
styles.add(ParagraphStyle("ReportH1", fontName="Arial-Bold", fontSize=16, leading=22,
                          textColor=colors.black, spaceBefore=18, spaceAfter=12, keepWithNext=True))
styles.add(ParagraphStyle("ReportH2", fontName="Arial-Bold", fontSize=12, leading=17,
                          textColor=colors.black, spaceBefore=12, spaceAfter=7, keepWithNext=True))
styles.add(ParagraphStyle("ReportCaption", fontName="Arial-Italic", fontSize=9, leading=13,
                          textColor=GREY, spaceBefore=6, spaceAfter=13, keepWithNext=False))
styles.add(ParagraphStyle("TableCaption", parent=styles["ReportCaption"], keepWithNext=True))
styles.add(ParagraphStyle("ReportCell", fontName=FONT, fontSize=9, leading=12.5, textColor=INK))
styles.add(ParagraphStyle("ReportCellHead", parent=styles["ReportCell"], fontName="Arial-Bold"))
styles.add(ParagraphStyle("ReportCode", fontName="Courier", fontSize=8.5, leading=12,
                          textColor=INK, spaceBefore=6, spaceAfter=12))
styles.add(ParagraphStyle("ReportReference", parent=styles["ReportBody"], fontSize=9,
                          leading=13.5, spaceAfter=10, wordWrap="CJK"))
styles.add(ParagraphStyle("ReportSmall", parent=styles["ReportBody"], fontSize=9,
                          leading=14, textColor=GREY))


def rich(text: str) -> str:
    text = html.escape(text, quote=False)
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"`(.+?)`", r'<font name="Courier">\1</font>', text)
    text = re.sub(r"https://[^\s<>]+", lambda m: f'<link href="{m.group(0)}" color="#333333">{m.group(0)}</link>', text)
    return text


def para(text, style="ReportBody"):
    return Paragraph(rich(text), styles[style])


def arrow(d, x1, y1, x2, y2, colour=GREY):
    d.add(Line(x1, y1, x2, y2, strokeColor=colour, strokeWidth=1))
    if x2 > x1:
        points = [x2, y2, x2 - 6, y2 + 3, x2 - 6, y2 - 3]
    elif x2 < x1:
        points = [x2, y2, x2 + 6, y2 + 3, x2 + 6, y2 - 3]
    else:
        direction = 1 if y2 > y1 else -1
        points = [x2, y2, x2 - 3, y2 - 6 * direction, x2 + 3, y2 - 6 * direction]
    d.add(Polygon(points, fillColor=colour, strokeColor=colour))


def box(d, x, y, w, h, label, sublabel=""):
    d.add(Rect(x, y, w, h, rx=5, ry=5, fillColor=colors.HexColor("#f5f6f3"), strokeColor=BORDER))
    d.add(String(x + w/2, y + h/2 + (5 if sublabel else -3), label,
                 fontName="Arial-Bold", fontSize=9, fillColor=INK, textAnchor="middle"))
    if sublabel:
        d.add(String(x + w/2, y + h/2 - 9, sublabel, fontName=FONT,
                     fontSize=7.8, fillColor=GREY, textAnchor="middle"))


def architecture():
    d = Drawing(WIDTH, 183)
    box(d, 5, 105, 115, 52, "Browser", "Untrusted requests")
    box(d, 168, 105, 146, 52, "Django application", "Permissions and workflow")
    box(d, 360, 105, 115, 52, "SQLite records", "Private fields encrypted")
    arrow(d, 120, 131, 168, 131)
    arrow(d, 314, 131, 360, 131)
    d.add(Line(145, 92, 145, 171, strokeColor=GREY, strokeDashArray=[3, 3]))
    d.add(String(145, 177, "Request boundary", fontName=FONT, fontSize=7.6, textAnchor="middle"))
    box(d, 168, 18, 146, 50, "Local secret material", "Outside Git history")
    box(d, 360, 18, 115, 50, "Property officer", "Physical ownership check")
    arrow(d, 241, 105, 241, 68)
    d.add(Line(314, 117, 335, 117, strokeColor=GREY, strokeWidth=1))
    d.add(Line(335, 117, 335, 43, strokeColor=GREY, strokeWidth=1))
    arrow(d, 335, 43, 360, 43)
    d.add(String(7, 28, "Local HTTP only", fontName=FONT, fontSize=8, fillColor=GREY))
    d.add(String(7, 15, "HTTPS deployment pending", fontName=FONT, fontSize=8, fillColor=GREY))
    return d


def workflow():
    d = Drawing(WIDTH, 162)
    d.add(String(6, 147, "Claim", fontName="Arial-Bold", fontSize=9))
    box(d, 67, 112, 105, 42, "Pending")
    box(d, 218, 112, 105, 42, "Approved")
    box(d, 369, 112, 105, 42, "Collected")
    arrow(d, 172, 133, 218, 133)
    arrow(d, 323, 133, 369, 133)
    d.add(String(195, 143, "Review", fontName=FONT, fontSize=7, textAnchor="middle"))
    d.add(String(346, 143, "Valid code", fontName=FONT, fontSize=7, textAnchor="middle"))
    box(d, 67, 51, 105, 34, "Rejected")
    arrow(d, 119, 112, 119, 85)
    d.add(String(133, 94, "Not approved", fontName=FONT, fontSize=7))
    d.add(String(6, 13, "Item", fontName="Arial-Bold", fontSize=9))
    for x, title in [(67, "Available"), (218, "Reserved"), (369, "Returned")]:
        box(d, x, 0, 105, 31, title)
    arrow(d, 172, 15, 218, 15)
    arrow(d, 323, 15, 369, 15)
    return d


class Heading(Paragraph):
    def __init__(self, text, level, key):
        super().__init__(rich(text), styles["ReportH1" if level == 0 else "ReportH2"])
        self.outline_text = text
        self.outline_level = level
        self.outline_key = key


class ReportDoc(SimpleDocTemplate):
    def afterFlowable(self, flowable):
        if isinstance(flowable, Heading):
            self.canv.bookmarkPage(flowable.outline_key)
            self.canv.addOutlineEntry(flowable.outline_text, flowable.outline_key,
                                      flowable.outline_level, False)
            heading_pages[flowable.outline_key] = self.page
        elif isinstance(flowable, Paragraph) and flowable.style.name in ("ReportCaption", "TableCaption"):
            label = flowable.getPlainText()
            match = re.match(r"^(Figure|Table) ([1-4]) ", label)
            if match:
                key = match.group(1).lower() + "-" + match.group(2)
                self.canv.bookmarkPage(key)
                heading_pages[key] = self.page


class NavigationEntry(Flowable):
    def __init__(self, label, key, small=False):
        super().__init__()
        self.label = para(label, "ReportSmall" if small else "ReportBody")
        self.key = key
        self.number = previous_pages.get(key, "")

    def wrap(self, available_width, available_height):
        self.width = available_width
        _, self.label_height = self.label.wrap(available_width - 29, available_height)
        self.height = self.label_height + 9
        return self.width, self.height

    def draw(self):
        self.label.drawOn(self.canv, 0, 9)
        self.canv.setFont(FONT, 9)
        self.canv.setFillColor(INK)
        self.canv.drawRightString(self.width, self.height - 11, str(self.number))
        self.canv.linkRect("", self.key, (0, 0, self.width, self.height), relative=1, thickness=0)


def footer(canvas, doc):
    canvas.saveState()
    if doc.page > 1:
        canvas.setFont(FONT, 8)
        canvas.setFillColor(GREY)
        canvas.drawString(56, 31, "ClaimSafe   Security coursework report")
        canvas.drawRightString(PAGE_W - 56, 31, str(doc.page))
    canvas.restoreState()


for filename in ("handover.jpg", "audit.jpg"):
    if not (ASSETS / filename).is_file():
        raise FileNotFoundError(f"Missing versioned report asset: {filename}")
drawings = {"architecture.svg": architecture(), "workflow.svg": workflow()}
for filename, drawing in drawings.items():
    renderSVG.drawToFile(drawing, str(ASSETS / filename))

text = SOURCE.read_text(encoding="utf-8")
navigation_path = REPO / ".local" / "report-build" / "navigation.json"
navigation_path.parent.mkdir(parents=True, exist_ok=True)
previous_pages = json.loads(navigation_path.read_text()) if navigation_path.exists() else {}
heading_pages = {}
body = text.split("## 1 Introduction", 1)[1].split("## References", 1)[0]
count = len(re.findall(r"\b[\w]+(?:['’-][\w]+)*\b", body))
story = [Spacer(1, 92), para("ClaimSafe", "ReportSmall"),
         para("Secure Campus Lost Property Claim and Collection System", "ReportTitle"),
         Spacer(1, 20), para("Security 6000CMD and 6005CEM"),
         para("Secure Application Development and Implementation"),
         Spacer(1, 24), para("Report draft for review", "ReportSmall"),
         para("25 October 2026", "ReportSmall"),
         para("Examined repository version d1086b5", "ReportSmall"),
         para(f"Main report approximately {round(count / 10) * 10:,} words", "ReportSmall"),
         Spacer(1, 30), para("The local application and automated test results are evaluated here. HTTPS deployment and the full vulnerability assessment remain outstanding.", "ReportSmall"),
         PageBreak(), para("Contents", "ReportH1")]

for label, key in [("1 Introduction and system overview", "section-1"),
                   ("2 Security analysis and design", "section-2"),
                   ("3 Security implementation and testing", "section-3"),
                   ("4 Discussion and improvement", "section-4"),
                   ("5 Summary", "section-5"), ("References", "references"),
                   ("Appendix A Implementation extracts", "appendix-a"),
                   ("Appendix B Assistance acknowledgement and submission materials", "appendix-b")]:
    story.append(NavigationEntry(label, key))
story.extend([Spacer(1, 24), para("Figures", "ReportH2")])
for label in ["1 Application components and trust boundaries", "2 Claim and item state transitions",
              "3 Fictional collection completed through the browser", "4 Restricted audit dashboard during the fictional walkthrough"]:
    story.append(NavigationEntry(label, "figure-" + label.split()[0], True))
story.extend([Spacer(1, 12), para("Tables", "ReportH2")])
for label in ["1 Role and resource access", "2 Prioritised threats", "3 Selected automated checks from the passing test run"]:
    story.append(NavigationEntry(label, "table-" + label.split()[0], True))
story.append(PageBreak())

lines = text.split("## 1 Introduction", 1)[1]
lines = ("## 1 Introduction" + lines).splitlines()
i = 0
reference_mode = False
heading_counter = 0
while i < len(lines):
    line = lines[i].strip()
    if not line:
        i += 1
        continue
    if line.startswith("## "):
        title = line[3:]
        if title == "References":
            reference_mode = True
            story.append(PageBreak())
            key = "references"
        elif title.startswith("Appendix A"):
            reference_mode = False
            story.append(PageBreak())
            key = "appendix-a"
        elif title.startswith("Appendix B"):
            key = "appendix-b"
        else:
            key = "section-" + title.split()[0]
        story.append(Heading(title, 0, key))
        i += 1
        continue
    if line.startswith("### "):
        heading_counter += 1
        story.append(Heading(line[4:], 1, f"sub-{heading_counter}"))
        i += 1
        continue
    if line.startswith("!["):
        match = re.fullmatch(r"!\[(.*?)\]\((.*?)\)", line)
        caption, location = match.groups()
        filename = Path(location).name
        if filename in drawings:
            visual = drawings[filename]
        else:
            visual = Image(str(ASSETS / filename))
            scale = WIDTH / visual.imageWidth
            visual.drawWidth = WIDTH
            visual.drawHeight = visual.imageHeight * scale
        story.append(KeepTogether([Spacer(1, 5), visual, para(caption, "ReportCaption")]))
        i += 1
        continue
    if line in {"Table 1 Role and resource access", "Table 2 Prioritised threats", "Table 3 Selected automated checks from the passing test run"}:
        story.append(para(line, "TableCaption"))
        i += 1
        continue
    if line.startswith("|"):
        rows = []
        while i < len(lines) and lines[i].strip().startswith("|"):
            row = [value.strip() for value in lines[i].strip().strip("|").split("|")]
            if not all(re.fullmatch(r":?-+:?", value) for value in row):
                rows.append(row)
            i += 1
        n = len(rows[0])
        widths = ([WIDTH * .37, WIDTH * .15, WIDTH * .23, WIDTH * .25] if n == 4
                  else [WIDTH * .34, WIDTH * .13, WIDTH * .53] if n == 3
                  else [WIDTH * .53, WIDTH * .47])
        cells = [[para(value, "ReportCellHead" if r == 0 else "ReportCell")
                  for value in row] for r, row in enumerate(rows)]
        table = Table(cells, colWidths=widths, repeatRows=1, hAlign="LEFT")
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eceff2")),
            ("GRID", (0, 0), (-1, -1), .5, BORDER),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ]))
        story.extend([table, Spacer(1, 12)])
        continue
    if line.startswith("```"):
        code = []
        i += 1
        while i < len(lines) and not lines[i].startswith("```"):
            code.append(lines[i])
            i += 1
        story.append(Preformatted("\n".join(code), styles["ReportCode"], maxLineLength=105))
        i += 1
        continue
    paragraph = [line]
    i += 1
    while i < len(lines) and lines[i].strip() and not lines[i].startswith(("#", "|", "![", "```", "Table ")):
        paragraph.append(lines[i].strip())
        i += 1
    story.append(para(" ".join(paragraph), "ReportReference" if reference_mode else "ReportBody"))

document = ReportDoc(str(OUTPUT), pagesize=A4, rightMargin=56, leftMargin=56,
                     topMargin=51, bottomMargin=51,
                     title="ClaimSafe Secure Campus Lost Property Claim and Collection System",
                     author="", subject="Security coursework report", pageCompression=1)
document.build(story, onFirstPage=footer, onLaterPages=footer)
navigation_path.write_text(json.dumps(heading_pages), encoding="utf-8")
shutil.copyfile(SOURCE, OUTPUT_DIR / "ClaimSafe_Report_Draft.md")
if (OUTPUT_DIR / "report-assets").resolve() != ASSETS.resolve():
    shutil.copytree(ASSETS, OUTPUT_DIR / "report-assets", dirs_exist_ok=True)
if previous_pages != heading_pages and not args.single_pass:
    subprocess.run([sys.executable, __file__, "--output-dir", str(OUTPUT_DIR), "--single-pass"], check=True)
    raise SystemExit(0)

from pypdf import PdfReader
reader = PdfReader(OUTPUT)
print(json.dumps({"pdf": str(OUTPUT), "pages": len(reader.pages), "main_words": count,
                  "source": str(SOURCE)}, indent=2))
