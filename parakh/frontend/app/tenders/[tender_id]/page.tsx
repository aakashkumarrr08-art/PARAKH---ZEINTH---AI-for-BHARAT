"use client";

import Link from "next/link";
import { FormEvent, useEffect, useMemo, useState } from "react";

import { EmptyState, Panel, StatusPill, formatDate } from "../../components";
import {
  Criterion,
  Manifest,
  Tender,
  approveManifest,
  generateManifest,
  getLatestManifest,
  getTender,
  updateManifest,
  uploadTenderDocument
} from "../../api-client";

type EditableCriterion = Criterion & { thresholdText: string };

function toEditable(criteria: Criterion[]): EditableCriterion[] {
  return criteria.map((criterion) => ({
    ...criterion,
    thresholdText: JSON.stringify(criterion.normalized_threshold, null, 2)
  }));
}

export default function TenderDetailPage({ params }: { params: { tender_id: string } }) {
  const tenderId = params.tender_id;
  const [tender, setTender] = useState<Tender | null>(null);
  const [manifest, setManifest] = useState<Manifest | null>(null);
  const [criteriaDraft, setCriteriaDraft] = useState<EditableCriterion[]>([]);
  const [docType, setDocType] = useState("NIT");
  const [file, setFile] = useState<File | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([getTender(tenderId), getLatestManifest(tenderId).catch(() => null)])
      .then(([tenderPayload, manifestPayload]) => {
        setTender(tenderPayload);
        setManifest(manifestPayload);
        setCriteriaDraft(manifestPayload ? toEditable(manifestPayload.criteria) : []);
      })
      .catch((err) => setError(err.message));
  }, [tenderId]);

  const manifestIsEditable = manifest?.status === "DRAFT";

  const uploadedDocCount = useMemo(() => tender?.documents.length ?? 0, [tender]);

  async function handleUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file) return;
    try {
      const updated = await uploadTenderDocument(tenderId, docType, file);
      setTender(updated);
      setFile(null);
      setMessage("Tender document uploaded.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed.");
    }
  }

  async function handleGenerateManifest() {
    try {
      const payload = await generateManifest(tenderId);
      setManifest(payload);
      setCriteriaDraft(toEditable(payload.criteria));
      setMessage("Draft manifest generated from the seeded evaluation criteria.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Manifest generation failed.");
    }
  }

  async function handleSaveManifest() {
    if (!manifest) return;
    try {
      const criteria = criteriaDraft.map(({ thresholdText, ...criterion }) => ({
        ...criterion,
        normalized_threshold: JSON.parse(thresholdText)
      })) as Criterion[];
      const payload = await updateManifest(tenderId, manifest._id, criteria);
      setManifest(payload);
      setCriteriaDraft(toEditable(payload.criteria));
      setMessage("Draft manifest saved.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Manifest save failed. Check threshold JSON formatting.");
    }
  }

  async function handleApproveManifest() {
    if (!manifest) return;
    try {
      const payload = await approveManifest(tenderId, manifest._id);
      setManifest(payload);
      setCriteriaDraft(toEditable(payload.criteria));
      setMessage("Manifest approved. Bidder evaluations can now run against this version.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Manifest approval failed.");
    }
  }

  return (
    <div className="space-y-6">
      <Panel
        title={tender?.title ?? "Tender"}
        kicker="Tender Detail"
        actions={
          <div className="flex flex-wrap gap-2">
            {tender ? <StatusPill value={tender.status} /> : null}
            {manifest ? <StatusPill value={manifest.status} /> : null}
          </div>
        }
      >
        {!tender ? (
          <EmptyState title="Loading tender" body="Fetching tender metadata and the latest criteria manifest." />
        ) : (
          <div className="grid gap-5 lg:grid-cols-[1.15fr,0.85fr]">
            <div className="space-y-3 text-sm leading-7 text-slate-700">
              <p>{tender.description || "No description provided."}</p>
              <p>
                <span className="font-semibold text-slate-900">Entity:</span> {tender.procuring_entity}
              </p>
              <p>
                <span className="font-semibold text-slate-900">Bid Reference:</span> {tender.bid_reference}
              </p>
              <p>
                <span className="font-semibold text-slate-900">Bid Validity End:</span> {tender.bid_validity_end || "Not set"}
              </p>
              <div className="flex flex-wrap gap-2 pt-2">
                <Link href={`/tenders/${tenderId}/bidders`} className="button-primary">
                  Open Bidder Console
                </Link>
              </div>
            </div>
            <div className="panel-muted p-5 text-sm text-slate-700">
              <p className="section-title">Readiness Snapshot</p>
              <div className="mt-4 space-y-3">
                <p>
                  Uploaded tender docs: <span className="font-semibold text-slate-900">{uploadedDocCount}</span>
                </p>
                <p>
                  Latest manifest version: <span className="font-semibold text-slate-900">{manifest?.version ?? "Not generated"}</span>
                </p>
                <p>
                  Approved by: <span className="font-semibold text-slate-900">{manifest?.approved_by || "Pending"}</span>
                </p>
                <p>
                  Approved at: <span className="font-semibold text-slate-900">{formatDate(manifest?.approved_at)}</span>
                </p>
              </div>
            </div>
          </div>
        )}
        {message ? <p className="mt-4 text-sm text-emerald-700">{message}</p> : null}
        {error ? <p className="mt-4 text-sm text-rose-700">{error}</p> : null}
      </Panel>

      <div className="grid gap-6 xl:grid-cols-[0.9fr,1.35fr]">
        <Panel title="Tender Documents" kicker="TUE Entry Point">
          <form className="space-y-4" onSubmit={handleUpload}>
            <select className="field" value={docType} onChange={(event) => setDocType(event.target.value)}>
              {["NIT", "QR", "Annexure", "Corrigendum", "ATC"].map((type) => (
                <option key={type} value={type}>
                  {type}
                </option>
              ))}
            </select>
            <input className="field" type="file" onChange={(event) => setFile(event.target.files?.[0] ?? null)} required />
            <button className="button-primary" type="submit">
              Upload Tender Document
            </button>
          </form>

          <div className="mt-6 space-y-3">
            {tender?.documents.length ? (
              tender.documents.map((document) => (
                <div key={document.document_id} className="panel-muted flex items-center justify-between gap-3 p-4 text-sm text-slate-700">
                  <div>
                    <p className="font-semibold text-slate-900">{document.filename}</p>
                    <p>{document.doc_type}</p>
                  </div>
                  <span className="text-xs text-slate-500">{formatDate(document.uploaded_at)}</span>
                </div>
              ))
            ) : (
              <EmptyState title="No tender documents yet" body="Upload the NIT, QR, annexures, or corrigenda to complete the tender intake trail." />
            )}
          </div>
        </Panel>

        <Panel
          title="Criteria Manifest"
          kicker="Admin / Tech / Capacity"
          actions={
            <div className="flex flex-wrap gap-2">
              <button className="button-secondary" type="button" onClick={handleGenerateManifest}>
                Generate Draft
              </button>
              {manifestIsEditable ? (
                <>
                  <button className="button-secondary" type="button" onClick={handleSaveManifest}>
                    Save Draft
                  </button>
                  <button className="button-primary" type="button" onClick={handleApproveManifest}>
                    Approve Manifest
                  </button>
                </>
              ) : null}
            </div>
          }
        >
          {!manifest ? (
            <EmptyState title="No manifest yet" body="Generate the initial manifest from the seeded evaluation criteria once the tender has been created." />
          ) : (
            <div className="space-y-5">
              {criteriaDraft.map((criterion, index) => (
                <div key={criterion.criterion_id} className="panel-muted p-5">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <p className="section-title">{criterion.stage}</p>
                      <p className="mt-2 text-lg font-semibold text-slate-900">
                        {index + 1}. {criterion.factor}
                      </p>
                      <p className="mt-2 text-sm text-slate-600">
                        {criterion.type} · {criterion.classification}
                      </p>
                    </div>
                    <StatusPill value={criterion.classification === "hard" ? "Deterministic" : "Manual Review"} />
                  </div>

                  <div className="mt-4 grid gap-4">
                    <textarea
                      className="field min-h-24"
                      value={criterion.description}
                      disabled={!manifestIsEditable}
                      onChange={(event) =>
                        setCriteriaDraft((current) =>
                          current.map((item) => (item.criterion_id === criterion.criterion_id ? { ...item, description: event.target.value } : item))
                        )
                      }
                    />
                    <textarea
                      className="field min-h-40 font-mono text-xs"
                      value={criterion.thresholdText}
                      disabled={!manifestIsEditable}
                      onChange={(event) =>
                        setCriteriaDraft((current) =>
                          current.map((item) => (item.criterion_id === criterion.criterion_id ? { ...item, thresholdText: event.target.value } : item))
                        )
                      }
                    />
                    <textarea
                      className="field min-h-24"
                      value={criterion.guidance_notes || ""}
                      disabled={!manifestIsEditable}
                      onChange={(event) =>
                        setCriteriaDraft((current) =>
                          current.map((item) => (item.criterion_id === criterion.criterion_id ? { ...item, guidance_notes: event.target.value } : item))
                        )
                      }
                    />
                  </div>

                  <div className="mt-4 rounded-2xl bg-white/70 p-4 text-sm text-slate-700">
                    <p className="font-semibold text-slate-900">Expected Evidence</p>
                    <ul className="mt-2 space-y-2">
                      {criterion.evidence_template.map((template) => (
                        <li key={`${criterion.criterion_id}-${template.doc_name}`}>
                          {template.doc_name}: {template.required_fields.join(", ")}
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Panel>
      </div>
    </div>
  );
}
