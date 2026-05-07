from __future__ import annotations

import json
from pathlib import Path

import fitz
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    Image,
    ListFlowable,
    ListItem,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.platypus.tableofcontents import TableOfContents


ROOT = Path(__file__).resolve().parents[2]
BUILD_DIR = ROOT / "deliverables" / "build"
WORKSPACE_DIR = ROOT / "deliverables" / "workspace"
ASSET_DIR = WORKSPACE_DIR / "assets"
OUTPUT_DIR = ROOT / "deliverables" / "final"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

PDF_PATH = OUTPUT_DIR / "PARAKH_Platform_Instruction_Manual.pdf"
QA_DIR = WORKSPACE_DIR / "manual_qa"
QA_DIR.mkdir(parents=True, exist_ok=True)

DATA = json.loads((BUILD_DIR / "project_data.json").read_text(encoding="utf-8"))


class ManualDocTemplate(BaseDocTemplate):
    def __init__(self, filename: str, **kwargs):
        super().__init__(filename, **kwargs)
        frame = Frame(self.leftMargin, self.bottomMargin, self.width, self.height, id="normal")
        template = PageTemplate(id="manual", frames=[frame], onPage=draw_page_chrome)
        self.addPageTemplates([template])

    def afterFlowable(self, flowable):
        if isinstance(flowable, Paragraph):
            style_name = flowable.style.name
            if style_name in {"Heading1Manual", "Heading2Manual", "Heading3Manual"}:
                level = {"Heading1Manual": 0, "Heading2Manual": 1, "Heading3Manual": 2}[style_name]
                self.notify("TOCEntry", (level, flowable.getPlainText(), self.page))


def draw_page_chrome(canvas, doc):
    canvas.saveState()
    width, height = A4
    if doc.page > 1:
        canvas.setStrokeColor(colors.HexColor("#D6D3CD"))
        canvas.setLineWidth(0.8)
        canvas.line(doc.leftMargin, height - 44, width - doc.rightMargin, height - 44)
        canvas.line(doc.leftMargin, 36, width - doc.rightMargin, 36)
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#5C6C7C"))
        canvas.drawString(doc.leftMargin, height - 32, "PARAKH Platform Instruction Manual")
        canvas.drawRightString(width - doc.rightMargin, height - 32, DATA["project"]["theme"])
        canvas.drawString(doc.leftMargin, 24, DATA["project"]["name"])
        canvas.drawRightString(width - doc.rightMargin, 24, f"Page {doc.page}")
    canvas.restoreState()


def build_styles():
    base = getSampleStyleSheet()
    styles = {
        "TitleCover": ParagraphStyle(
            "TitleCover",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=28,
            leading=34,
            textColor=colors.HexColor("#10233A"),
            alignment=TA_LEFT,
            spaceAfter=8,
        ),
        "SubtitleCover": ParagraphStyle(
            "SubtitleCover",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=13,
            leading=18,
            textColor=colors.HexColor("#5C6C7C"),
            alignment=TA_LEFT,
            spaceAfter=8,
        ),
        "Heading1Manual": ParagraphStyle(
            "Heading1Manual",
            parent=base["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=24,
            textColor=colors.HexColor("#1F5D8E"),
            spaceBefore=16,
            spaceAfter=8,
        ),
        "Heading2Manual": ParagraphStyle(
            "Heading2Manual",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=19,
            textColor=colors.HexColor("#10233A"),
            spaceBefore=12,
            spaceAfter=6,
        ),
        "Heading3Manual": ParagraphStyle(
            "Heading3Manual",
            parent=base["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=16,
            textColor=colors.HexColor("#10233A"),
            spaceBefore=10,
            spaceAfter=4,
        ),
        "BodyManual": ParagraphStyle(
            "BodyManual",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=10.5,
            leading=15,
            textColor=colors.HexColor("#2F3E4D"),
            alignment=TA_JUSTIFY,
            spaceAfter=7,
        ),
        "BodyLeft": ParagraphStyle(
            "BodyLeft",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=10.5,
            leading=15,
            textColor=colors.HexColor("#2F3E4D"),
            alignment=TA_LEFT,
            spaceAfter=7,
        ),
        "SmallManual": ParagraphStyle(
            "SmallManual",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#5C6C7C"),
            alignment=TA_LEFT,
            spaceAfter=5,
        ),
        "Callout": ParagraphStyle(
            "Callout",
            parent=base["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=15,
            textColor=colors.HexColor("#10233A"),
            alignment=TA_LEFT,
            spaceAfter=6,
        ),
        "TOCHeading": ParagraphStyle(
            "TOCHeading",
            parent=base["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=22,
            textColor=colors.HexColor("#1F5D8E"),
            spaceBefore=6,
            spaceAfter=10,
        ),
    }
    return styles


STYLES = build_styles()


def p(text: str, style: str = "BodyManual") -> Paragraph:
    return Paragraph(text, STYLES[style])


def spacer(height: float = 0.12) -> Spacer:
    return Spacer(1, height * inch)


def bullet_list(items: list[str]) -> ListFlowable:
    return ListFlowable(
        [ListItem(p(item, "BodyLeft")) for item in items],
        bulletType="bullet",
        bulletFontName="Helvetica",
        bulletFontSize=9,
        leftIndent=16,
        bulletOffsetY=2,
    )


def numbered_list(items: list[str]) -> ListFlowable:
    return ListFlowable(
        [ListItem(p(item, "BodyLeft")) for item in items],
        bulletType="1",
        leftIndent=18,
        bulletFontName="Helvetica",
        bulletFontSize=9,
        bulletOffsetY=2,
    )


def table_block(rows: list[list[str]], widths: list[float], header_fill: str = "#E8EEF5") -> Table:
    header_style = ParagraphStyle(
        "TableHeaderCell",
        parent=STYLES["SmallManual"],
        fontName="Helvetica-Bold",
        fontSize=8.8,
        leading=10.5,
        textColor=colors.HexColor("#10233A"),
        alignment=TA_LEFT,
    )
    body_style = ParagraphStyle(
        "TableBodyCell",
        parent=STYLES["SmallManual"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=10.5,
        textColor=colors.HexColor("#2F3E4D"),
        alignment=TA_LEFT,
    )
    cooked_rows: list[list[Paragraph]] = []
    for row_index, row in enumerate(rows):
        style = header_style if row_index == 0 else body_style
        cooked_rows.append([Paragraph(str(cell), style) for cell in row])

    table = Table(cooked_rows, colWidths=widths, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(header_fill)),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#C9D3DF")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return table


def scaled_image(path: Path, max_width: float, max_height: float) -> Image:
    image = Image(str(path))
    iw, ih = image.imageWidth, image.imageHeight
    scale = min(max_width / iw, max_height / ih)
    image.drawWidth = iw * scale
    image.drawHeight = ih * scale
    return image


def cover_page(story: list):
    story.append(Spacer(1, 1.1 * inch))
    story.append(p(DATA["project"]["name"], "TitleCover"))
    story.append(p(DATA["project"]["full_name"], "SubtitleCover"))
    story.append(spacer(0.1))
    story.append(p(DATA["project"]["theme"], "Callout"))
    story.append(p(DATA["project"]["tagline"], "BodyLeft"))
    story.append(spacer(0.2))
    story.append(scaled_image(ASSET_DIR / "artifact_montage.png", 6.4 * inch, 4.7 * inch))
    story.append(spacer(0.18))
    story.append(p("<b>Core principle:</b> " + DATA["project"]["philosophy"], "BodyManual"))
    story.append(spacer(0.08))
    story.append(p(f"<b>Prepared for:</b> {DATA['project']['team_name']}", "BodyLeft"))
    story.append(p("<b>Team:</b> " + ", ".join(DATA["project"]["team_members"]), "BodyLeft"))
    story.append(p("<b>Prepared on:</b> 6 May 2026", "BodyLeft"))
    story.append(PageBreak())


def toc_page(story: list):
    story.append(p("Table of Contents", "TOCHeading"))
    toc = TableOfContents()
    toc.levelStyles = [
        ParagraphStyle(name="TOCLevel1", fontName="Helvetica", fontSize=10.5, leading=14, leftIndent=12, firstLineIndent=-8, spaceBefore=4),
        ParagraphStyle(name="TOCLevel2", fontName="Helvetica", fontSize=9.5, leading=12, leftIndent=26, firstLineIndent=-8, textColor=colors.HexColor("#41515F")),
        ParagraphStyle(name="TOCLevel3", fontName="Helvetica", fontSize=9, leading=11, leftIndent=40, firstLineIndent=-8, textColor=colors.HexColor("#6A7783")),
    ]
    story.append(toc)
    story.append(PageBreak())


def feature_definition() -> list[dict]:
    return [
        {
            "heading": "6.1 Dashboard and Tender Portfolio",
            "purpose": "Provide a high-level operating picture by combining tender volume, bidder activity, disqualification count, override count, and audit-event count in one officer-first landing page.",
            "prerequisites": ["Backend API running", "Frontend running", "Officer login token available (the UI auto-signs in with the seeded officer account)"],
            "inputs": ["Authenticated session", "Existing tender and bidder data in MongoDB"],
            "outputs": ["Dashboard metrics", "Links into the tender portfolio and bidder workflow"],
            "steps": [
                "Open the frontend root page and confirm the officer profile pill is visible.",
                "Review the metric tiles for Tenders, Bidders, Disqualifications, Auto Resolved, Overrides, and Audit Events.",
                "Open an active tender from the dashboard or navigate to the Tenders page to continue the workflow."
            ],
            "notes": ["The dashboard statistics are generated from the audit service and MongoDB counts, so they reflect current platform state."],
        },
        {
            "heading": "6.2 Tender Creation",
            "purpose": "Create the authority-side container that will hold procurement metadata, uploaded tender documents, and the manifest approval trail.",
            "prerequisites": ["Officer or admin role", "Frontend access to /tenders", "Backend API /api/tenders available"],
            "inputs": ["Tender title", "Procuring entity", "Bid reference", "Optional description", "Optional bid validity end date"],
            "outputs": ["A new tender record with status ACTIVE and a dedicated document workspace"],
            "steps": [
                "Navigate to the Tenders page and complete the Create Tender form.",
                "Submit the form to create the tender record in MongoDB.",
                "Confirm the new tender appears in the Tender Portfolio list and open Manage Manifest or Open Bidders to continue."
            ],
            "notes": ["The repo seeds a sample CRPF tender automatically at startup, so tender creation can be demonstrated either from scratch or using seeded data."],
        },
        {
            "heading": "6.3 Tender Document Upload",
            "purpose": "Attach the source tender-side files that define procurement rules, attachments, corrigenda, and terms.",
            "prerequisites": ["Tender already created", "Officer or admin role"],
            "inputs": ["Document type such as NIT, QR, Annexure, Corrigendum, or ATC", "Selected file upload"],
            "outputs": ["Stored tender document under /uploads/tenders/<tender_id>/", "Updated tender document history"],
            "steps": [
                "Open the Tender Detail page for the target tender.",
                "Choose the document type from the dropdown.",
                "Select the tender-side file and click Upload Tender Document.",
                "Verify that the file appears in the Tender Documents list with filename, type, and upload timestamp."
            ],
            "notes": ["Document uploads are traceable by document id and relative path and become the evidence base for manifest generation."],
        },
        {
            "heading": "6.4 Manifest Generation, Review, and Approval",
            "purpose": "Produce the structured criteria blueprint used for evaluation and ensure only approved manifest versions can drive verdicting.",
            "prerequisites": ["Tender exists", "Officer or admin role", "Tender document workspace opened"],
            "inputs": ["Generate Draft action", "Optional edits to criterion description, threshold JSON, or guidance notes"],
            "outputs": ["Draft or approved criteria manifest version", "latest_manifest_id linkage on the tender record"],
            "steps": [
                "Click Generate Draft on the Tender Detail page to create a new manifest version from the seeded evaluation criteria.",
                "Review each criterion by stage, factor, rule type, classification, threshold JSON, and guidance notes.",
                "Adjust descriptions or thresholds if the tender requires localized interpretation.",
                "Click Save Draft to persist edits.",
                "Click Approve Manifest when the version is ready for bidder evaluation."
            ],
            "notes": ["Only DRAFT manifests are editable. Approving a new manifest supersedes any earlier APPROVED version for the same tender."],
        },
        {
            "heading": "6.5 Bidder Registration",
            "purpose": "Create a bidder-side record scoped to the tender and initialize the checklist that governs required uploads.",
            "prerequisites": ["Target tender exists", "Officer or admin role"],
            "inputs": ["Bidder name", "Bidder type (OEM or Authorized Bidder)", "Optional OEM name"],
            "outputs": ["Bidder record with PENDING overall status", "Checklist status initialized from fixture CSV"],
            "steps": [
                "Open the tender's Bidder Console.",
                "Enter bidder identity details in the Register Bidder form.",
                "Submit the form and confirm the bidder appears in the left-side bidder list.",
                "Select the bidder to display the document checklist and subsequent actions."
            ],
            "notes": ["The bidder type matters because non-OEM bidders require OEM Authorization evidence to avoid administrative disqualification."],
        },
        {
            "heading": "6.6 Bidder Document Upload",
            "purpose": "Collect every bidder-side file expected by the checklist and maintain per-document status visibility.",
            "prerequisites": ["Bidder already registered", "Checklist visible on the Bidder Console"],
            "inputs": ["Checklist document name", "Uploaded file for that document slot"],
            "outputs": ["Stored bidder document under /uploads/bidders/<tender_id>/<bidder_id>/", "Checklist item marked Uploaded"],
            "steps": [
                "Choose a file for a checklist row such as Industrial License, EMD Proof, or Technical Compliance.",
                "Click Upload <document name> for the relevant row.",
                "Repeat until all required documents are uploaded or until the demo scope is satisfied.",
                "Use the uploaded filename and status pill to confirm each checklist state update."
            ],
            "notes": ["The checklist is driven by backend/app/fixtures/bidder_doc_checklist.csv, so it can be adapted tender by tender in future releases."],
        },
        {
            "heading": "6.7 Evidence Ingestion and Extraction",
            "purpose": "Transform bidder submissions into text previews, structured fields, extraction methods, and confidence scores suitable for evaluation.",
            "prerequisites": ["At least one bidder document uploaded", "OCR/runtime dependencies available for image-based files"],
            "inputs": ["Ingest Documents action"],
            "outputs": ["Extracted evidence records in MongoDB", "Field-level confidence scores and text preview"],
            "steps": [
                "On the selected bidder's checklist panel, click Ingest Documents.",
                "Allow the backend to process each file according to its type: digital PDF, image, HTML, or fallback.",
                "Open the Evaluation Workbench after ingestion and inspect the linked evidence to confirm extraction results."
            ],
            "notes": [
                "Digital-text PDFs are read through PyMuPDF or pdfplumber first. OCR is only used when native text extraction is not available.",
                "The prototype currently extracts fields such as PAN, GSTIN, EMD amount/date, ballistic levels, turnover averages, size mix, OEM authorization, and experience years."
            ],
        },
        {
            "heading": "6.8 Evaluation Workbench",
            "purpose": "Give officers criterion-level visibility into the rules applied, evidence used, extracted values, and automatic verdict generated.",
            "prerequisites": ["Approved manifest available", "Bidder evidence already ingested"],
            "inputs": ["Evaluate Bidder action or Re-run Evaluation action"],
            "outputs": ["New AUTO_EVAL events", "Updated bidder overall status", "Disqualification reasons when applicable"],
            "steps": [
                "Click Evaluate Bidder from the Bidder Console or Re-run Evaluation from the workbench.",
                "Select a criterion from the left-side event list.",
                "Review stage, criterion name, auto verdict, final verdict, evidence quality, and event hash.",
                "Inspect text previews and extracted values associated with the criterion."
            ],
            "notes": [
                "The evaluation engine assigns Eligible, Not Eligible, or Needs Manual Review based on evidence completeness, confidence threshold, and rule type.",
                "Hard disqualification flags are surfaced explicitly rather than hidden inside free-form model output."
            ],
        },
        {
            "heading": "6.9 Officer Override and Reason Capture",
            "purpose": "Preserve officer sovereignty by allowing controlled overrides with structured reasoning and append-only history.",
            "prerequisites": ["Evaluation events exist for the bidder", "Officer or admin role"],
            "inputs": ["Selected criterion", "Final verdict choice", "Reason code", "Optional reviewer notes"],
            "outputs": ["New OVERRIDE event", "Updated bidder overall status", "Persistent reason trace"],
            "steps": [
                "Select the criterion to override in the workbench.",
                "Choose the final verdict from the dropdown.",
                "Select an appropriate reason code such as LOW_CONFIDENCE_CONFIRMED or OCR_FALSE_NEGATIVE.",
                "Add reviewer notes where contextual explanation is useful.",
                "Click Record Override and verify the confirmation message."
            ],
            "notes": ["Overrides do not mutate prior events. Instead, they create a new event with prior_event_id and a new event hash."],
        },
        {
            "heading": "6.10 Audit Timeline Review",
            "purpose": "Present a grouped, criterion-wise history of automated evaluations and officer overrides for scrutiny, explanation, and export preparation.",
            "prerequisites": ["At least one evaluation run completed"],
            "inputs": ["Open Audit action from the bidder console"],
            "outputs": ["Criterion-grouped event timeline with verdict changes, evidence references, and hash-chain metadata"],
            "steps": [
                "Open the audit page for the bidder.",
                "Review the total event count summary.",
                "Expand each criterion grouping and inspect sequence order, event type, timestamps, verdicts, evidence docs, event hash, and prior event id.",
                "Use this screen to narrate why a bidder passed, failed, or remained under review."
            ],
            "notes": ["This view is particularly valuable for hackathon judging because it visualizes both transparency and governance discipline."],
        },
        {
            "heading": "6.11 Excel and PDF Export",
            "purpose": "Convert the evaluation ledger into external reporting artifacts that can be shared with stakeholders, auditors, or judges.",
            "prerequisites": ["Audit history available for the target bidder"],
            "inputs": ["Export Excel or Export PDF action"],
            "outputs": ["audit_report.xlsx", "audit_report.pdf"],
            "steps": [
                "Open the Audit Timeline page.",
                "Click Export Excel to produce the structured workbook report.",
                "Click Export PDF to produce the narrative audit report.",
                "Retrieve files from the browser download flow or the backend audit export directory."
            ],
            "notes": ["Exports are stored under /uploads/audit_exports/<tender_id>/<bidder_id>/ in the backend upload tree."],
        },
        {
            "heading": "6.12 Demo Reference Files",
            "purpose": "Use the repository's provided tender and bidder sample files to demonstrate the complete platform without fabricating evidence.",
            "prerequisites": ["Access to the project workspace"],
            "inputs": ["Files from Tendor Docs/, Bidder Docs/, and REPO and INFO/"],
            "outputs": ["Consistent demo narrative backed by real sample artifacts"],
            "steps": [
                "Use Tendor Docs/ for tender-side uploads such as notice, bid doc, evaluation criteria, and annexures.",
                "Use Bidder Docs/ for bidder-side checklist uploads.",
                "Use REPO and INFO/ documents to explain the philosophy, theme fit, and hackathon story during presentation."
            ],
            "notes": ["These reference files are explicitly cited in the repo README as recommended demo inputs."],
        },
    ]


def troubleshooting_definition() -> list[list[str]]:
    return [
        ["Frontend opens but data does not load", "Backend is not running, NEXT_PUBLIC_API_BASE is incorrect, or the login token is stale.", "Confirm backend health at /health, verify NEXT_PUBLIC_API_BASE=http://localhost:8000/api, and reload the page."],
        ["Bidder ingestion returns weak or empty evidence", "The file is image-heavy, OCR tooling is unavailable, or the source file is low quality.", "Use clearer sample files, ensure Tesseract is installed for scanned inputs, and prefer digital PDFs when possible."],
        ["Manifest cannot be edited", "The current version is already approved.", "Generate a new draft manifest or edit only while the manifest status is DRAFT."],
        ["Evaluation remains under review", "Required evidence is missing, low confidence, or the criterion is subjective by design.", "Open the workbench, inspect missing docs or low-confidence fields, and use an officer override if justified."],
        ["Exports do not appear", "No audit history exists yet or export directory permissions are blocked.", "Run evaluation first, then re-open the audit page and repeat export after confirming backend write access."],
        ["MongoDB connection error", "MongoDB is not running or MONGO_URI is incorrect.", "Start MongoDB first, then confirm the configured connection string matches the active runtime."],
        ["Frontend dev server fails on Windows PowerShell", "PowerShell script policy blocks the npm shim.", "Use cmd /c npm.cmd install and cmd /c npm.cmd run dev as documented in the README."],
    ]


def glossary_definition() -> list[list[str]]:
    return [
        ["Tender", "A government request inviting suppliers to bid for goods or services."],
        ["Bidder", "A supplier or consortium participating in the tender."],
        ["Manifest", "The structured evaluation blueprint generated from tender-side criteria."],
        ["Criterion", "One rule or requirement to test during bidder evaluation."],
        ["Evidence", "The extracted text and structured fields sourced from bidder documents."],
        ["Hard Disqualification", "A confirmed failure condition that should lead to rejection unless policy allows otherwise."],
        ["Graduated Criterion", "A criterion that may need officer interpretation instead of full automation."],
        ["Needs Manual Review", "A verdict state used when confidence is low, evidence is missing, or the rule is subjective."],
        ["Reason Code", "A structured label used to explain an officer override."],
        ["Event Hash", "A SHA-256 digest stored for each evaluation or override event to make the audit trail tamper-evident."],
        ["RTI", "Right to Information; a transparency framework under which procurement decisions may later be questioned."],
        ["CAG / Vigilance", "Oversight and audit mechanisms that can review procurement decisions and supporting records."],
    ]


def add_feature_section(story: list, feature: dict):
    story.append(p(feature["heading"], "Heading2Manual"))
    story.append(p(feature["purpose"], "BodyManual"))
    overview_rows = [
        ["Attribute", "Detail"],
        ["Purpose", feature["purpose"]],
        ["Prerequisites", "<br/>".join(feature["prerequisites"])],
        ["Inputs", "<br/>".join(feature["inputs"])],
        ["Outputs", "<br/>".join(feature["outputs"])],
    ]
    story.append(table_block(overview_rows, [1.55 * inch, 4.75 * inch]))
    story.append(spacer(0.08))
    story.append(p("Procedure", "Heading3Manual"))
    story.append(numbered_list(feature["steps"]))
    if feature.get("notes"):
        story.append(spacer(0.02))
        story.append(p("Operational Notes", "Heading3Manual"))
        story.append(bullet_list(feature["notes"]))
    story.append(spacer(0.08))


def build_story() -> list:
    story: list = []
    cover_page(story)
    toc_page(story)

    story.append(p("1. Executive Summary", "Heading1Manual"))
    story.append(
        p(
            "PARAKH is a prototype for AI-assisted tender evaluation in Indian government procurement, designed specifically around the realities of CRPF-style eligibility analysis. "
            "Its defining principle is that AI should not become a black-box sovereign decision-maker. Instead, the platform should help officers work faster while preserving explainability, consistency, and a defensible audit trail.",
            "BodyManual",
        )
    )
    story.append(
        p(
            "In practice, PARAKH connects tender-side rules, bidder-side evidence, deterministic evaluation logic, and officer-led overrides into one coherent workflow. "
            "This manual serves two audiences at once: technical users who need to install and run the platform, and operational users or presenters who need to understand what the platform does, when to use each feature, and how to explain its outputs.",
            "BodyManual",
        )
    )
    story.append(bullet_list(DATA["problem_points"]))
    story.append(spacer(0.08))

    story.append(p("2. Platform Overview", "Heading1Manual"))
    story.append(p(DATA["project"]["tagline"], "Callout"))
    story.append(p("The platform is organized into four tightly connected subsystems.", "BodyManual"))
    module_rows = [["Module", "Role in the platform"]]
    for module in DATA["modules"]:
        module_rows.append([f"{module['id']} - {module['name']}", module["purpose"]])
    story.append(table_block(module_rows, [2.15 * inch, 4.15 * inch]))
    story.append(spacer(0.08))
    story.append(scaled_image(ASSET_DIR / "solution_workflow.png", 6.4 * inch, 3.5 * inch))
    story.append(spacer(0.1))
    story.append(p("Why the solution fits the theme and problem", "Heading2Manual"))
    story.append(bullet_list(DATA["fit_points"]))

    story.append(p("3. System Prerequisites and Installation", "Heading1Manual"))
    story.append(
        p(
            "The repository supports three practical operating tracks: Docker Compose for integrated startup, a Windows quick-start path using included batch scripts and local runtime assets, and manual local development for backend and frontend work.",
            "BodyManual",
        )
    )
    story.append(p("3.1 Recommended software baseline", "Heading2Manual"))
    prereq_rows = [
        ["Component", "Recommended version or expectation", "Purpose"],
        ["Node.js", "20.x or compatible runtime", "Run the Next.js frontend"],
        ["Python", "3.11 or compatible", "Run FastAPI backend and document-processing libraries"],
        ["MongoDB", "7.x or 8.x", "Primary operational database"],
        ["Redis", "7.x (optional in current prototype)", "Reserved for future async worker integration"],
        ["Tesseract OCR", "Installed locally for image-based extraction", "Improve OCR on scanned bidder files"],
        ["Docker Desktop", "Current version", "Run the complete stack through docker-compose"],
    ]
    story.append(table_block(prereq_rows, [1.4 * inch, 2.05 * inch, 2.95 * inch]))
    story.append(spacer(0.08))

    story.append(p("3.2 Docker setup", "Heading2Manual"))
    story.append(numbered_list([
        "Open a terminal in the parakh/ folder.",
        "Run docker-compose up --build.",
        "Wait for the frontend, backend, MongoDB, and Redis containers to become healthy.",
        "Open http://localhost:3000 for the frontend and http://localhost:8000/docs for backend API documentation.",
    ]))

    story.append(p("3.3 Local Windows quick start using included scripts", "Heading2Manual"))
    story.append(numbered_list([
        "Open three separate terminals from the parakh/ root.",
        "Run .\\start-mongo-local.cmd to start the embedded MongoDB server against local-runtime/data/db.",
        "Run .\\start-backend-local.cmd to start the FastAPI backend on port 8000.",
        "Run .\\start-frontend-local.cmd to start the Next.js frontend on port 3000.",
    ]))
    story.append(p("The local runtime folder already includes a MongoDB distribution and downloaded Tesseract installer assets for Windows-oriented demonstration flows.", "SmallManual"))

    story.append(p("3.4 Manual backend setup", "Heading2Manual"))
    story.append(numbered_list([
        "Change into parakh/backend.",
        "Create a virtual environment: python -m venv .venv",
        "Activate the environment.",
        "Install dependencies: pip install -r requirements.txt",
        "Start the API: uvicorn app.main:app --reload",
    ]))

    story.append(p("3.5 Manual frontend setup", "Heading2Manual"))
    story.append(numbered_list([
        "Change into parakh/frontend.",
        "Install frontend packages: npm install",
        "Set NEXT_PUBLIC_API_BASE to http://localhost:8000/api if required.",
        "Run npm run dev.",
        "On Windows PowerShell, use cmd /c npm.cmd install and cmd /c npm.cmd run dev if the npm shim is blocked by script policy.",
    ]))

    story.append(p("3.6 Environment variables and configuration", "Heading2Manual"))
    env_rows = [["Variable", "Purpose"]]
    env_map = {
        "MONGO_URI": "MongoDB connection string used by the backend.",
        "MONGO_DB": "Target database name; default is parakh.",
        "REDIS_URL": "Reserved queue/cache connection for future asynchronous processing.",
        "JWT_SECRET": "Secret used to sign and verify access tokens.",
        "JWT_ALGORITHM": "JWT signing algorithm; the prototype defaults to HS256.",
        "NEXT_PUBLIC_API_BASE": "Frontend base URL for the backend API.",
        "TESSERACT_CMD": "Optional explicit path to the Tesseract executable.",
        "TESSDATA_PREFIX": "Optional tessdata directory override for OCR language packs.",
    }
    for var in DATA["runtime"]["environment_variables"]:
        env_rows.append([var, env_map.get(var, "Project runtime variable.")])
    story.append(table_block(env_rows, [1.7 * inch, 4.7 * inch]))

    story.append(p("4. Getting Started: Run the Platform End-to-End", "Heading1Manual"))
    story.append(numbered_list([
        "Start MongoDB first, then backend, then frontend.",
        "Open the frontend in the browser and let the auto-login flow acquire the seeded officer token.",
        "Confirm backend health at /health and frontend data loading on the dashboard.",
        "Open the sample CRPF tender or create a new tender.",
        "Upload tender-side documents and approve the manifest.",
        "Register a bidder, upload checklist documents, ingest evidence, evaluate the bidder, and export reports.",
    ]))
    story.append(spacer(0.08))
    story.append(scaled_image(ASSET_DIR / "demo_flow.png", 6.25 * inch, 3.75 * inch))
    story.append(spacer(0.08))
    account_rows = [["Seeded account", "Role", "Use case"]]
    for account in DATA["runtime"]["demo_accounts"]:
        account_rows.append([account["username"], account["role"], "Administrative setup" if account["role"] == "ADMIN" else "Day-to-day review and evaluation"])
    story.append(table_block(account_rows, [1.4 * inch, 1.0 * inch, 3.95 * inch]))

    story.append(p("5. User Roles, Access, and Navigation", "Heading1Manual"))
    story.append(
        p(
            "The backend exposes JWT-protected APIs and supports two roles: ADMIN and OFFICER. The frontend currently auto-signs in with the seeded officer account for demonstration convenience, but the backend still enforces role checks on protected actions.",
            "BodyManual",
        )
    )
    role_rows = [
        ["Role", "Typical responsibilities"],
        ["ADMIN", "Provision or supervise tenders, review manifests, and support operating governance."],
        ["OFFICER", "Upload documents, evaluate bidders, inspect evidence, record overrides, and export audit reports."],
    ]
    story.append(table_block(role_rows, [1.2 * inch, 5.2 * inch]))
    story.append(spacer(0.08))
    story.append(p("Primary navigation surfaces are Dashboard, Tenders, Bidder Hub, the Tender Detail page, the Bidder Console, the Evaluation Workbench, and the Audit Timeline.", "BodyManual"))

    story.append(p("6. Feature Documentation", "Heading1Manual"))
    story.append(p("This section documents every core platform function in an operator-first format.", "BodyManual"))
    story.append(scaled_image(ASSET_DIR / "artifact_montage.png", 6.4 * inch, 3.25 * inch))
    story.append(spacer(0.08))
    for feature in feature_definition():
        add_feature_section(story, feature)

    story.append(p("7. Technical Architecture", "Heading1Manual"))
    story.append(
        p(
            "The frontend is a Next.js application that consumes FastAPI endpoints exposed under /api. FastAPI coordinates MongoDB persistence, upload storage, evidence extraction, deterministic evaluation logic, and reporting services. The architecture is intentionally simple enough for a hackathon prototype but already organized around real operational boundaries.",
            "BodyManual",
        )
    )
    story.append(scaled_image(ASSET_DIR / "system_architecture.png", 6.4 * inch, 3.55 * inch))
    story.append(spacer(0.08))
    stack_rows = [["Layer", "Implementation detail"]]
    stack_rows.extend(
        [
            ["Frontend", ", ".join(DATA["tech_stack"]["frontend"])],
            ["Backend", ", ".join(DATA["tech_stack"]["backend"])],
            ["Database", ", ".join(DATA["tech_stack"]["database"])],
            ["Document AI", ", ".join(DATA["tech_stack"]["document_ai"])],
            ["Export services", ", ".join(DATA["tech_stack"]["exports"])],
            ["Security", ", ".join(DATA["tech_stack"]["security"])],
            ["Infrastructure", ", ".join(DATA["tech_stack"]["infra"])],
        ]
    )
    story.append(table_block(stack_rows, [1.4 * inch, 5.0 * inch]))
    story.append(spacer(0.08))
    story.append(p("Evaluation decision model", "Heading2Manual"))
    story.append(scaled_image(ASSET_DIR / "verdict_logic.png", 6.2 * inch, 3.45 * inch))

    story.append(p("8. Data, Files, and Configuration Structure", "Heading1Manual"))
    story.append(
        p(
            "Operational persistence is split across MongoDB collections, fixture files, and upload folders. This separation makes the prototype easy to reason about during demonstrations and future expansion.",
            "BodyManual",
        )
    )
    collection_rows = [
        ["Repository area", "Purpose"],
        ["backend/app/fixtures", "Evaluation criteria, disqualification factors, bidder checklist, and policy configuration"],
        ["backend/app/uploads/tenders", "Tender-side uploaded files"],
        ["backend/app/uploads/bidders", "Bidder-side uploaded files"],
        ["backend/app/uploads/audit_exports", "Generated PDF and Excel audit reports"],
        ["MongoDB users", "Stored users and roles"],
        ["MongoDB tenders", "Tender metadata and manifest linkage"],
        ["MongoDB criteria_manifest_versions", "Versioned manifests"],
        ["MongoDB bidders", "Bidder records and checklist state"],
        ["MongoDB extracted_evidence", "Structured evidence extracted from documents"],
        ["MongoDB evaluation_events", "Append-only evaluation and override history"],
    ]
    story.append(table_block(collection_rows, [2.4 * inch, 4.0 * inch]))
    story.append(spacer(0.08))
    story.append(p("Prototype constraints and known limitations", "Heading2Manual"))
    story.append(bullet_list(DATA["prototype_limits"]))

    story.append(p("9. Troubleshooting", "Heading1Manual"))
    story.append(
        p(
            "The following issues are the most likely to appear during setup or hackathon demonstration. Each entry pairs the symptom with the probable cause and the recommended action.",
            "BodyManual",
        )
    )
    story.append(table_block(troubleshooting_definition(), [1.65 * inch, 2.15 * inch, 2.55 * inch], header_fill="#F2F4F7"))

    story.append(p("10. Operational Best Practices", "Heading1Manual"))
    story.append(bullet_list([
        "Approve a manifest only after thresholds, descriptions, and guidance notes reflect the tender being demonstrated.",
        "Use higher-quality digital PDFs whenever possible; reserve scanned image demos for cases where OCR behavior itself is part of the story.",
        "Treat Needs Manual Review as a feature, not a weakness. It shows that the platform refuses false certainty when evidence is incomplete or subjective.",
        "Always finish a live demo on the audit timeline or exported report so judges see the governance advantage clearly.",
        "For non-OEM bidders, remember to demonstrate how missing OEM Authorization affects disqualification logic.",
    ]))

    story.append(p("11. Glossary", "Heading1Manual"))
    story.append(table_block([["Term", "Definition"]] + glossary_definition(), [1.55 * inch, 4.85 * inch]))

    story.append(p("12. Appendices", "Heading1Manual"))
    story.append(p("12.1 Seeded evaluation criteria", "Heading2Manual"))
    criteria_rows = [["Criterion", "Why it matters"]]
    criteria_notes = {
        "EMD Validity": "Commercial seriousness and bid security.",
        "Legal Standing": "Baseline authorization and tax identity.",
        "Protection Level": "Life-safety compliance against ballistic standards.",
        "Design/Pattern": "Tender-specific technical conformity that often needs officer review.",
        "Sizing Accuracy": "Operational fit against the required size distribution.",
        "Turnover Depth": "Financial capacity to execute the contract.",
        "Supply History": "Experience and comparability of prior work."
    }
    for criterion in DATA["criteria"]:
        criteria_rows.append([criterion, criteria_notes[criterion]])
    story.append(table_block(criteria_rows, [2.0 * inch, 4.4 * inch]))
    story.append(spacer(0.08))

    story.append(p("12.2 Bidder checklist reference", "Heading2Manual"))
    checklist_rows = [["Document", "Operational purpose"]]
    for item in DATA["checklist_docs"]:
        checklist_rows.append([item["name"], item["purpose"]])
    story.append(table_block(checklist_rows, [2.1 * inch, 4.3 * inch]))
    story.append(spacer(0.08))

    story.append(p("12.3 Override reason codes", "Heading2Manual"))
    reason_rows = [["Reason code", "When to use it"]]
    reason_use = {
        "LOW_CONFIDENCE_CONFIRMED": "The officer checked low-confidence evidence and still accepts or rejects the extraction outcome.",
        "ADDITIONAL_EVIDENCE_ACCEPTED": "The decision was clarified by supplementary evidence or context.",
        "POLICY_EXCEPTION_APPROVED": "A policy-authorized exception was applied under officer responsibility.",
        "OCR_FALSE_NEGATIVE": "OCR missed a valid signal that the officer confirmed manually.",
        "OFFICER_INTERPRETATION": "Human interpretation was necessary because the criterion is subjective or contextual.",
        "DOCUMENT_SCOPE_CLARIFIED": "The officer determined that the document does or does not satisfy the intended scope.",
    }
    for code in DATA["reason_codes"]:
        reason_rows.append([code, reason_use[code]])
    story.append(table_block(reason_rows, [2.25 * inch, 4.15 * inch]))
    story.append(spacer(0.08))

    story.append(p("12.4 Core commands for presenters and developers", "Heading2Manual"))
    command_rows = [
        ["Scenario", "Command or script"],
        ["Docker startup", "docker-compose up --build"],
        ["Windows local MongoDB", ".\\start-mongo-local.cmd"],
        ["Windows local backend", ".\\start-backend-local.cmd"],
        ["Windows local frontend", ".\\start-frontend-local.cmd"],
        ["Backend dev", "uvicorn app.main:app --reload"],
        ["Frontend dev", "npm run dev"],
    ]
    story.append(table_block(command_rows, [2.0 * inch, 4.4 * inch]))
    story.append(spacer(0.12))

    story.append(
        p(
            "End of manual. This document is intended to function as both an operational runbook and a hackathon presentation aid for PARAKH.",
            "BodyManual",
        )
    )
    return story


def render_pdf_pages(pdf_path: Path, target_dir: Path, max_pages: int = 5) -> None:
    doc = fitz.open(pdf_path)
    for index in range(min(max_pages, doc.page_count)):
        page = doc.load_page(index)
        pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False)
        pix.save(target_dir / f"manual-page-{index + 1:02d}.png")
    doc.close()


def main() -> None:
    doc = ManualDocTemplate(
        str(PDF_PATH),
        pagesize=A4,
        leftMargin=0.8 * inch,
        rightMargin=0.8 * inch,
        topMargin=0.72 * inch,
        bottomMargin=0.68 * inch,
        title="PARAKH Platform Instruction Manual",
        author=DATA["project"]["team_name"],
    )
    doc.build(build_story())
    render_pdf_pages(PDF_PATH, QA_DIR, max_pages=6)
    print(f"Manual written to {PDF_PATH}")


if __name__ == "__main__":
    main()
