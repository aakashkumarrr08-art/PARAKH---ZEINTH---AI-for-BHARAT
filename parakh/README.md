# PARAKH Prototype

PARAKH stands for **Procurement Audit-Ready Assessment & Knowledge Harnessing**. This prototype is a monorepo for AI-assisted tender evaluation in Indian government procurement, designed around a simple rule:

> The system does not make sovereign eligibility decisions. It makes evidence, logic, and officer actions transparent, consistent, and defensible.

## Stack

- Backend: FastAPI, Motor, MongoDB, Pydantic
- OCR/PDF: PyMuPDF, pdfplumber, pdf2image, OpenCV, Tesseract
- Frontend: Next.js App Router, TypeScript, TailwindCSS
- Async infra: Redis stubbed for future worker integration
- Auth: JWT with `ADMIN` and `OFFICER`

## What is included

- Tender creation and document upload
- Draft manifest generation from `evaluation_criteria.csv`
- Bidder registration plus checklist-driven document upload
- Deterministic evidence extraction and rule evaluation
- Three-state verdicting: `Eligible`, `Not Eligible`, `Needs Manual Review`
- Hard disqualification flagging
- Officer override flow with reason codes
- Append-only, hash-chained evaluation events
- Audit timeline plus Excel/PDF export

## Repo layout

```text
parakh/
  docker-compose.yml
  backend/
  frontend/
```

## Fixtures

The backend seeds configuration from:

- `backend/app/fixtures/evaluation_criteria.csv`
- `backend/app/fixtures/disqualification_factors.csv`
- `backend/app/fixtures/bidder_doc_checklist.csv`
- `backend/app/fixtures/policy.yaml`

At startup, PARAKH also seeds:

- Demo `admin / admin123`
- Demo `officer / officer123`
- A sample CRPF tender with a draft manifest template

## Run with Docker

From the `parakh/` folder:

```bash
docker-compose up --build
```

Then open:

- Frontend: [http://localhost:3000](http://localhost:3000)
- Backend docs: [http://localhost:8000/docs](http://localhost:8000/docs)
- Health: [http://localhost:8000/health](http://localhost:8000/health)

## Local development

### Backend

```bash
cd backend
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

On Windows PowerShell:

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

On this Windows machine, PowerShell script policy blocks the plain `npm` shim. Use:

```powershell
cd frontend
cmd /c npm.cmd install
cmd /c npm.cmd run dev
```

## Local Windows quick start without Docker

This repo now includes local runtime assets for Windows:

- MongoDB server extracted under `local-runtime/mongodb/`
- Local MongoDB data dir under `local-runtime/data/db`
- Tesseract installed under `C:\Program Files\Tesseract-OCR`

You can start the stack with three separate terminals from the repo root:

```powershell
.\start-mongo-local.cmd
.\start-backend-local.cmd
.\start-frontend-local.cmd
```

## Suggested demo flow

1. Open the dashboard and go to `Tenders`.
2. Create a tender or use the seeded CRPF sample.
3. Upload tender documents and click `Generate Draft`.
4. Review the manifest, optionally edit threshold JSON or notes, then click `Approve Manifest`.
5. Open the bidder console for that tender.
6. Register a bidder and upload checklist items.
7. Click `Ingest Documents` to populate `extracted_evidence`.
8. Click `Evaluate Bidder` to generate append-only `evaluation_events`.
9. Open the evaluation workbench to inspect criterion logic, evidence, and officer override controls.
10. Open the audit page and export the Excel or PDF report.

## Using the reference files already in this workspace

You already have example source materials next to this repo in the parent workspace, including:

- `Tendor Docs/`
- `Bidder Docs/`
- `REPO and INFO/`

Those can be used directly during demo uploads to show the tender intake and bidder submission flow.

## Key implementation principles

- Deterministic rules drive automated verdict suggestions.
- Low-confidence or missing evidence never causes a silent rejection.
- Subjective checks stay officer-reviewable.
- Every evaluation or override is inserted as a new event; prior history is preserved.
- LLM-like behavior is restricted to stubs such as clause tagging, not final verdicting.

## Notes

- OCR is implemented as a best-effort prototype pipeline. Digital-text PDFs work best.
- The current Redis service is present for future task queue integration, but not yet wired to workers.
- The frontend auto-signs in with the seeded officer account for convenience.
