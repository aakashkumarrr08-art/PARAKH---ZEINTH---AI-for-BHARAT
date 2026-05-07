from __future__ import annotations

import json
import math
import shutil
from pathlib import Path

import fitz
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
BUILD_DIR = ROOT / "deliverables" / "build"
WORKSPACE_DIR = ROOT / "deliverables" / "workspace"
ASSET_DIR = WORKSPACE_DIR / "assets"
DATA = json.loads((BUILD_DIR / "project_data.json").read_text(encoding="utf-8"))

PALETTE = {
    "bg": "#F6F1E7",
    "paper": "#FFFDFC",
    "ink": "#10233A",
    "muted": "#5C6C7C",
    "accent": "#C2892D",
    "accent_soft": "#E6D7BE",
    "blue": "#1F5D8E",
    "green": "#2E6A5E",
    "red": "#B24D3E",
    "line": "#D9D5CE",
}


def ensure_dirs() -> None:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)


def pick_font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    candidates = []
    if bold:
        candidates.extend(
            [
                "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
                "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
                "/System/Library/Fonts/Helvetica.ttc",
            ]
        )
    candidates.extend(
        [
            "/System/Library/Fonts/Supplemental/Arial.ttf",
            "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
            "/System/Library/Fonts/Supplemental/Times New Roman.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
        ]
    )
    for candidate in candidates:
        path = Path(candidate)
        if path.exists():
            try:
                return ImageFont.truetype(str(path), size=size)
            except OSError:
                continue
    return ImageFont.load_default()


def wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        trial = word if not current else f"{current} {word}"
        if draw.textlength(trial, font=font) <= max_width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or [text]


def draw_wrapped_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    box: tuple[int, int, int, int],
    font: ImageFont.ImageFont,
    fill: str,
    line_gap: int = 6,
    align: str = "left",
) -> int:
    x0, y0, x1, y1 = box
    max_width = x1 - x0
    lines = wrap_text(draw, text, font, max_width)
    _, line_height = draw.textbbox((0, 0), "Ag", font=font)[2:]
    y = y0
    for line in lines:
        line_width = draw.textlength(line, font=font)
        if align == "center":
            x = x0 + (max_width - line_width) / 2
        elif align == "right":
            x = x1 - line_width
        else:
            x = x0
        draw.text((x, y), line, font=font, fill=fill)
        y += line_height + line_gap
        if y > y1:
            break
    return y


def new_canvas(width: int, height: int) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    image = Image.new("RGB", (width, height), PALETTE["bg"])
    draw = ImageDraw.Draw(image)
    return image, draw


def add_header(draw: ImageDraw.ImageDraw, width: int, title: str, subtitle: str) -> None:
    draw.rectangle((0, 0, width, 96), fill=PALETTE["paper"])
    draw.rectangle((40, 26, 48, 78), fill=PALETTE["accent"])
    title_font = pick_font(34, bold=True)
    subtitle_font = pick_font(16)
    draw.text((68, 18), title, font=title_font, fill=PALETTE["ink"])
    draw.text((68, 58), subtitle, font=subtitle_font, fill=PALETTE["muted"])
    draw.line((40, 96, width - 40, 96), fill=PALETTE["line"], width=2)


def rounded_box(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], fill: str, outline: str = PALETTE["line"], radius: int = 18) -> None:
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=2)


def save_asset(image: Image.Image, name: str) -> Path:
    path = ASSET_DIR / name
    image.save(path)
    return path


def copy_reference_images() -> dict[str, Path]:
    copied: dict[str, Path] = {}
    for key in ("tender_notice", "bidder_checklist"):
        source = Path(DATA["sample_assets"][key])
        target = ASSET_DIR / f"{key}{source.suffix.lower()}"
        shutil.copy2(source, target)
        copied[key] = target

    pdf_path = Path(DATA["sample_assets"]["audit_report_pdf"])
    doc = fitz.open(pdf_path)
    page = doc.load_page(0)
    pix = page.get_pixmap(matrix=fitz.Matrix(1.7, 1.7), alpha=False)
    audit_preview = ASSET_DIR / "audit_report_page1.png"
    pix.save(audit_preview)
    copied["audit_report"] = audit_preview
    doc.close()
    return copied


def build_system_architecture() -> Path:
    image, draw = new_canvas(1600, 900)
    add_header(
        draw,
        1600,
        "PARAKH Technical Architecture",
        "End-to-end view of the frontend, API, data layer, AI processing path, and export services.",
    )

    title_font = pick_font(24, bold=True)
    body_font = pick_font(16)
    small_font = pick_font(14)

    left = (70, 180, 430, 420)
    center = (510, 150, 1085, 680)
    right = (1165, 180, 1530, 420)
    bottom_left = (140, 500, 470, 760)
    bottom_right = (1115, 500, 1460, 760)

    rounded_box(draw, left, "#FFF8EF")
    rounded_box(draw, center, "#F9FCFF")
    rounded_box(draw, right, "#F4FBF7")
    rounded_box(draw, bottom_left, "#FFFDFC")
    rounded_box(draw, bottom_right, "#FFFDFC")

    draw.text((96, 202), "Frontend Layer", font=title_font, fill=PALETTE["ink"])
    draw.text((538, 172), "Backend and Decision Core", font=title_font, fill=PALETTE["ink"])
    draw.text((1192, 202), "Data and Storage", font=title_font, fill=PALETTE["ink"])
    draw.text((168, 522), "AI-Assisted Extraction", font=title_font, fill=PALETTE["ink"])
    draw.text((1142, 522), "Audit and Reporting", font=title_font, fill=PALETTE["ink"])

    frontend_lines = [
        "Next.js 14 / React 18 interface",
        "Dashboard, Tender Console, Bidder Console",
        "Evaluation Workbench and Audit Timeline",
        "Auto-login using seeded officer account"
    ]
    y = 248
    for line in frontend_lines:
        draw_wrapped_text(draw, line, (96, y, 392, y + 32), body_font, PALETTE["muted"])
        y += 38

    modules = [
        ("Auth + Access", "JWT auth, ADMIN/OFFICER roles, /api/auth endpoints"),
        ("Tender Services", "Tender creation, document upload, manifest generation, manifest approval"),
        ("Bidder Services", "Checklist-driven upload, evidence extraction, status tracking"),
        ("Evaluation Engine", "Deterministic rules, hard disqualification flags, three-state verdicting"),
        ("Officer Overrides", "Reason codes, reviewer notes, append-only override events")
    ]
    y = 228
    for idx, (name, detail) in enumerate(modules):
        box = (540, y, 1052, y + 78)
        rounded_box(draw, box, PALETTE["paper"], radius=16)
        draw.text((560, y + 12), name, font=pick_font(19, bold=True), fill=PALETTE["blue"])
        draw_wrapped_text(draw, detail, (560, y + 38, 1015, y + 68), small_font, PALETTE["muted"])
        if idx < len(modules) - 1:
            draw.line((796, y + 78, 796, y + 104), fill=PALETTE["accent"], width=3)
            y += 98

    data_lines = [
        "MongoDB collections for users, tenders, manifests, bidders, extracted evidence, and evaluation events",
        "Upload folders for tender files, bidder files, and generated audit exports",
        "Indexed append-only event store for audit history and hash-chain verification"
    ]
    y = 248
    for line in data_lines:
        draw_wrapped_text(draw, line, (1192, y, 1490, y + 48), body_font, PALETTE["muted"])
        y += 62

    ai_lines = [
        "PyMuPDF and pdfplumber for digital-text PDFs",
        "pytesseract path support for scanned images",
        "Regex-based extraction for PAN, GSTIN, EMD, turnover, ballistic levels, and size mix",
        "Confidence scores determine whether automation proceeds or manual review is required"
    ]
    y = 565
    for line in ai_lines:
        draw_wrapped_text(draw, line, (168, y, 446, y + 42), small_font, PALETTE["muted"])
        y += 48

    report_lines = [
        "Audit timeline groups events by criterion",
        "Excel export via openpyxl",
        "PDF export via ReportLab",
        "Every event stores prior event id and SHA-256 event hash"
    ]
    y = 565
    for line in report_lines:
        draw_wrapped_text(draw, line, (1142, y, 1436, y + 42), small_font, PALETTE["muted"])
        y += 48

    arrow_color = PALETTE["accent"]
    draw.line((430, 300, 510, 300), fill=arrow_color, width=6)
    draw.polygon([(510, 300), (492, 290), (492, 310)], fill=arrow_color)
    draw.line((1085, 300, 1165, 300), fill=arrow_color, width=6)
    draw.polygon([(1165, 300), (1147, 290), (1147, 310)], fill=arrow_color)
    draw.line((720, 680, 305, 500), fill=PALETTE["blue"], width=4)
    draw.polygon([(305, 500), (326, 494), (318, 515)], fill=PALETTE["blue"])
    draw.line((875, 680, 1288, 500), fill=PALETTE["green"], width=4)
    draw.polygon([(1288, 500), (1268, 493), (1275, 514)], fill=PALETTE["green"])

    note_box = (520, 736, 1080, 830)
    rounded_box(draw, note_box, "#FBF6EC", outline=PALETTE["accent_soft"])
    draw.text((548, 756), "Design principle", font=pick_font(18, bold=True), fill=PALETTE["accent"])
    draw_wrapped_text(
        draw,
        "PARAKH keeps AI narrow, traceable, and subordinate to officer judgement. The system optimizes for defensibility, not blind automation.",
        (548, 790, 1040, 820),
        small_font,
        PALETTE["ink"],
    )

    return save_asset(image, "system_architecture.png")


def build_solution_workflow() -> Path:
    image, draw = new_canvas(1600, 900)
    add_header(
        draw,
        1600,
        "Solution Workflow",
        "Operational view of how tender rules and bidder evidence move through PARAKH from intake to export.",
    )

    title_font = pick_font(22, bold=True)
    body_font = pick_font(15)

    steps = [
        ("1", "Tender Intake", "Create a tender record and upload NIT, QR, annexures, corrigenda, and ATC files."),
        ("2", "Manifest Build", "Generate a draft criteria manifest, review threshold JSON, and approve the active version."),
        ("3", "Bidder Onboarding", "Register a bidder and open the checklist-driven submission workspace."),
        ("4", "Evidence Ingestion", "Upload bidder documents, extract text and fields, and store structured evidence."),
        ("5", "Rule Evaluation", "Match evidence to criteria, apply hard and graduated rules, and assign a three-state verdict."),
        ("6", "Officer Review", "Inspect logic, linked evidence, hard flags, and record overrides with reason codes."),
        ("7", "Audit Export", "Review the criterion timeline and export Excel or PDF reports for scrutiny.")
    ]

    x = 70
    y = 172
    box_w = 208
    box_h = 250
    gap = 20
    colors = ["#FFF8EF", "#F7FBFF", "#F4FBF7", "#FFFDFC", "#F7FBFF", "#FFF8EF", "#F4FBF7"]
    for idx, (number, title, detail) in enumerate(steps):
        xx = x + idx * (box_w + gap)
        rounded_box(draw, (xx, y, xx + box_w, y + box_h), colors[idx], radius=20)
        draw.ellipse((xx + 18, y + 18, xx + 64, y + 64), fill=PALETTE["accent"], outline=PALETTE["accent"])
        num_font = pick_font(24, bold=True)
        bbox = draw.textbbox((0, 0), number, font=num_font)
        draw.text((xx + 41 - (bbox[2] - bbox[0]) / 2, y + 27), number, font=num_font, fill="#FFFFFF")
        draw.text((xx + 18, y + 84), title, font=title_font, fill=PALETTE["ink"])
        draw_wrapped_text(draw, detail, (xx + 18, y + 126, xx + box_w - 18, y + box_h - 18), body_font, PALETTE["muted"])
        if idx < len(steps) - 1:
            mid_y = y + box_h / 2
            draw.line((xx + box_w, mid_y, xx + box_w + gap - 6, mid_y), fill=PALETTE["blue"], width=5)
            draw.polygon(
                [
                    (xx + box_w + gap - 6, mid_y),
                    (xx + box_w + gap - 24, mid_y - 10),
                    (xx + box_w + gap - 24, mid_y + 10),
                ],
                fill=PALETTE["blue"],
            )

    note_box = (90, 520, 1510, 804)
    rounded_box(draw, note_box, PALETTE["paper"], radius=22)
    draw.text((120, 548), "How the workflow maps to the codebase", font=pick_font(24, bold=True), fill=PALETTE["ink"])
    notes = [
        "Tender Intake and Manifest Build map to the TUE flow in the tender router and tender service.",
        "Bidder Onboarding and Evidence Ingestion map to the BDI flow in the bidder router and bidder service.",
        "Rule Evaluation and Officer Review map to the EARE and workbench flows in the evaluation service and evaluation page.",
        "Audit Export maps to the audit router and audit service, which generate xlsx and pdf outputs from the append-only event history."
    ]
    yy = 600
    for note in notes:
        draw.ellipse((126, yy + 4, 138, yy + 16), fill=PALETTE["accent"])
        draw_wrapped_text(draw, note, (154, yy, 1468, yy + 42), body_font, PALETTE["muted"])
        yy += 52

    return save_asset(image, "solution_workflow.png")


def build_verdict_logic() -> Path:
    image, draw = new_canvas(1400, 820)
    add_header(
        draw,
        1400,
        "Three-State Verdict Logic",
        "Core decision philosophy used by the evaluation engine and officer workbench.",
    )

    title_font = pick_font(26, bold=True)
    body_font = pick_font(16)

    center = 700
    top_y = 170

    rounded_box(draw, (520, top_y, 880, top_y + 110), "#F7FBFF", radius=20)
    draw.text((560, top_y + 20), "Approved Manifest + Extracted Evidence", font=title_font, fill=PALETTE["blue"])
    draw_wrapped_text(
        draw,
        "Each criterion is checked against the latest approved manifest using structured evidence fields and confidence scores.",
        (560, top_y + 62, 840, top_y + 98),
        body_font,
        PALETTE["muted"],
    )

    draw.line((700, 280, 700, 336), fill=PALETTE["accent"], width=5)
    draw.polygon([(700, 336), (688, 316), (712, 316)], fill=PALETTE["accent"])

    cards = [
        ((120, 360, 410, 610), "#F4FBF7", "Eligible", "All required evidence is present and high-confidence. Deterministic rules confirm the bidder meets the criterion."),
        ((555, 360, 845, 610), "#FFF8EF", "Needs Manual Review", "Any low-confidence extraction, missing required document, or subjective requirement is escalated to the officer instead of being silently rejected."),
        ((990, 360, 1280, 610), "#FFF4F1", "Not Eligible", "A hard rule failure or confirmed disqualification condition is recorded with traceable logic and supporting evidence.")
    ]

    for box, fill, title, detail in cards:
        rounded_box(draw, box, fill, radius=22)
        draw.text((box[0] + 24, box[1] + 24), title, font=title_font, fill=PALETTE["ink"])
        draw_wrapped_text(draw, detail, (box[0] + 24, box[1] + 78, box[2] - 24, box[3] - 24), body_font, PALETTE["muted"])

    draw.line((700, 336, 265, 360), fill=PALETTE["green"], width=4)
    draw.line((700, 336, 700, 360), fill=PALETTE["blue"], width=4)
    draw.line((700, 336, 1135, 360), fill=PALETTE["red"], width=4)

    footer = (120, 664, 1280, 760)
    rounded_box(draw, footer, PALETTE["paper"], radius=18)
    draw.text((150, 690), "Officer sovereignty is preserved at all times.", font=pick_font(22, bold=True), fill=PALETTE["ink"])
    draw_wrapped_text(
        draw,
        "When an officer overrides an outcome, PARAKH creates a new append-only event with the final verdict, reason code, reviewer id, notes, prior event reference, and SHA-256 event hash.",
        (150, 724, 1240, 748),
        body_font,
        PALETTE["muted"],
    )

    return save_asset(image, "verdict_logic.png")


def build_demo_flow() -> Path:
    image, draw = new_canvas(1400, 860)
    add_header(
        draw,
        1400,
        "Hackathon Demo Flow",
        "A judge-friendly script for demonstrating the platform in under five minutes.",
    )

    title_font = pick_font(24, bold=True)
    body_font = pick_font(15)
    small_font = pick_font(14)

    steps = [
        "Open the dashboard and show seeded activity counts.",
        "Open the CRPF sample tender and upload supporting tender files if needed.",
        "Generate or review the manifest to show structured criteria and thresholds.",
        "Register a bidder and upload checklist documents from the sample bidder folder.",
        "Run document ingestion and point out extracted evidence fields.",
        "Evaluate the bidder and walk through Eligible, Not Eligible, and Manual Review logic.",
        "Record an officer override, open the audit trail, and export Excel or PDF."
    ]

    for idx, step in enumerate(steps):
        y = 156 + idx * 92
        rounded_box(draw, (92, y, 1310, y + 70), "#FFFDFC" if idx % 2 == 0 else "#F8FBFE", radius=16)
        draw.rectangle((114, y + 14, 174, y + 56), fill=PALETTE["accent"])
        step_no = f"{idx + 1:02d}"
        step_font = pick_font(22, bold=True)
        bbox = draw.textbbox((0, 0), step_no, font=step_font)
        draw.text((144 - (bbox[2] - bbox[0]) / 2, y + 23), step_no, font=step_font, fill="#FFFFFF")
        draw_wrapped_text(draw, step, (206, y + 18, 1268, y + 48), body_font, PALETTE["ink"])
        hint = [
            "Use the Dashboard, Tenders, and Bidder Hub navigation.",
            "Point to tender metadata, status, and tender document history.",
            "Show stage, factor, thresholds, and approval status.",
            "Explain that checklist status is updated document by document.",
            "Call out extraction method, text preview, and confidence-aware field capture.",
            "Open the workbench and trace evidence to a specific criterion.",
            "End on the audit timeline to reinforce trust and defensibility."
        ][idx]
        draw_wrapped_text(draw, hint, (206, y + 46, 1268, y + 62), small_font, PALETTE["muted"])

    return save_asset(image, "demo_flow.png")


def build_sample_montage(refs: dict[str, Path]) -> Path:
    canvas, draw = new_canvas(1800, 980)
    add_header(
        draw,
        1800,
        "Reference Artifact Montage",
        "Real sample files from the project workspace used as tender-side, bidder-side, and audit-side proof objects.",
    )

    slots = [
        ("Tender-side Notice", "Sample tender intake file used to demonstrate tender upload and manifest context.", refs["tender_notice"], (70, 160, 590, 900)),
        ("Bidder Checklist", "Checklist reference used to map bidder upload requirements and expected evidence.", refs["bidder_checklist"], (640, 160, 1160, 900)),
        ("Audit Report Preview", "Generated output that shows how PARAKH turns event history into formal reporting artifacts.", refs["audit_report"], (1210, 160, 1730, 900)),
    ]

    title_font = pick_font(22, bold=True)
    body_font = pick_font(15)
    for title, note, source, box in slots:
        rounded_box(draw, box, PALETTE["paper"], radius=18)
        draw.text((box[0] + 20, box[1] + 20), title, font=title_font, fill=PALETTE["ink"])
        draw_wrapped_text(draw, note, (box[0] + 20, box[1] + 54, box[2] - 20, box[1] + 92), body_font, PALETTE["muted"])
        inner = (box[0] + 20, box[1] + 110, box[2] - 20, box[3] - 20)
        image = Image.open(source).convert("RGB")
        image.thumbnail((inner[2] - inner[0], inner[3] - inner[1]))
        px = inner[0] + ((inner[2] - inner[0]) - image.width) // 2
        py = inner[1] + ((inner[3] - inner[1]) - image.height) // 2
        canvas.paste(image, (px, py))

    return save_asset(canvas, "artifact_montage.png")


def main() -> None:
    ensure_dirs()
    refs = copy_reference_images()
    build_system_architecture()
    build_solution_workflow()
    build_verdict_logic()
    build_demo_flow()
    build_sample_montage(refs)
    print(f"Assets generated in {ASSET_DIR}")


if __name__ == "__main__":
    main()
