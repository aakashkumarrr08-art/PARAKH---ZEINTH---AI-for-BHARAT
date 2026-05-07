"use client";

import { useEffect, useMemo, useState } from "react";

import {
  Evidence,
  EvaluationEvent,
  EvaluationOverview,
  evaluateBidder,
  getEvaluation,
  getEvidence,
  getReasonCodes,
  overrideCriterion
} from "../../../api-client";
import { EmptyState, Panel, StatusPill } from "../../../components";

export default function EvaluationWorkbenchPage({ params }: { params: { tender_id: string; bidder_id: string } }) {
  const { tender_id: tenderId, bidder_id: bidderId } = params;
  const [overview, setOverview] = useState<EvaluationOverview | null>(null);
  const [evidence, setEvidence] = useState<Evidence[]>([]);
  const [reasonCodes, setReasonCodes] = useState<string[]>([]);
  const [selectedCriterionId, setSelectedCriterionId] = useState<string>("");
  const [finalVerdict, setFinalVerdict] = useState<"Eligible" | "Not Eligible" | "Needs Manual Review">("Needs Manual Review");
  const [reasonCode, setReasonCode] = useState("");
  const [reviewerNotes, setReviewerNotes] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([getEvaluation(tenderId, bidderId), getEvidence(tenderId, bidderId), getReasonCodes()])
      .then(([overviewPayload, evidencePayload, codes]) => {
        setOverview(overviewPayload);
        setEvidence(evidencePayload);
        setReasonCodes(codes);
        setReasonCode(codes[0] ?? "");
        if (overviewPayload.latest_events[0]) {
          setSelectedCriterionId(overviewPayload.latest_events[0].criterion_id);
        }
      })
      .catch((err) => setError(err.message));
  }, [bidderId, tenderId]);

  const selectedEvent = useMemo<EvaluationEvent | null>(
    () => overview?.latest_events.find((event) => event.criterion_id === selectedCriterionId) ?? overview?.latest_events[0] ?? null,
    [overview, selectedCriterionId]
  );

  useEffect(() => {
    if (!selectedEvent) return;
    setFinalVerdict(selectedEvent.final_verdict);
  }, [selectedEvent]);

  const supportingEvidence = useMemo(
    () =>
      selectedEvent
        ? evidence.filter((item) => selectedEvent.evidence_docs.some((doc) => doc.document_id === item.document_id))
        : [],
    [evidence, selectedEvent]
  );

  async function runEvaluation() {
    try {
      const payload = await evaluateBidder(tenderId, bidderId);
      setOverview(payload);
      if (payload.latest_events[0]) {
        setSelectedCriterionId(payload.latest_events[0].criterion_id);
      }
      setMessage("Evaluation refreshed.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not run evaluation.");
    }
  }

  async function submitOverride() {
    if (!selectedEvent || !reasonCode) return;
    try {
      const payload = await overrideCriterion(tenderId, bidderId, selectedEvent.criterion_id, {
        final_verdict: finalVerdict,
        reason_code: reasonCode,
        reviewer_notes: reviewerNotes
      });
      setOverview(payload);
      setMessage("Officer override recorded as a new append-only event.");
      setReviewerNotes("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Override failed.");
    }
  }

  return (
    <div className="space-y-6">
      <Panel
        title="Evaluation Workbench"
        kicker="EARE"
        actions={
          <div className="flex flex-wrap gap-2">
            {overview ? <StatusPill value={overview.overall_status} /> : null}
            {overview?.hard_disqualified ? <StatusPill value="DISQUALIFIED" /> : null}
            <button className="button-primary" type="button" onClick={runEvaluation}>
              Re-run Evaluation
            </button>
          </div>
        }
      >
        {message ? <p className="mb-4 text-sm text-emerald-700">{message}</p> : null}
        {error ? <p className="mb-4 text-sm text-rose-700">{error}</p> : null}

        {!overview?.latest_events.length ? (
          <EmptyState title="No evaluation events yet" body="Run evaluation after bidder ingestion to populate the criterion workbench." />
        ) : (
          <div className="grid gap-5 xl:grid-cols-[0.72fr,1.28fr]">
            <div className="space-y-3">
              {overview.latest_events.map((event) => (
                <button
                  key={event.criterion_id}
                  type="button"
                  onClick={() => setSelectedCriterionId(event.criterion_id)}
                  className={`w-full rounded-3xl border p-4 text-left transition ${selectedEvent?.criterion_id === event.criterion_id ? "border-amber-400 bg-amber-50" : "border-slate-200 bg-white/70"}`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="section-title">{event.stage}</p>
                      <p className="mt-2 font-semibold text-slate-900">{event.criterion_name}</p>
                    </div>
                    <StatusPill value={event.final_verdict} />
                  </div>
                  <p className="mt-3 text-sm text-slate-600">{event.criterion_type}</p>
                </button>
              ))}
            </div>

            {selectedEvent ? (
              <div className="space-y-5">
                <div className="panel-muted p-5">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <p className="section-title">{selectedEvent.stage}</p>
                      <p className="mt-2 text-2xl font-semibold text-slate-900">{selectedEvent.criterion_name}</p>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <StatusPill value={selectedEvent.auto_verdict} />
                      <StatusPill value={selectedEvent.final_verdict} />
                    </div>
                  </div>
                  <p className="mt-4 text-sm leading-7 text-slate-700">{selectedEvent.match_logic}</p>
                  <div className="mt-4 grid gap-3 md:grid-cols-2">
                    <div className="rounded-2xl bg-white/70 p-4 text-sm text-slate-700">
                      <p className="font-semibold text-slate-900">Evidence quality</p>
                      <p className="mt-2">{selectedEvent.evidence_quality}</p>
                    </div>
                    <div className="rounded-2xl bg-white/70 p-4 text-sm text-slate-700">
                      <p className="font-semibold text-slate-900">Audit chain</p>
                      <p className="mt-2 break-all text-xs">{selectedEvent.event_hash}</p>
                    </div>
                  </div>
                </div>

                <div className="panel-muted p-5">
                  <p className="section-title">Document / Evidence Viewer</p>
                  <div className="mt-4 space-y-4">
                    {supportingEvidence.length ? (
                      supportingEvidence.map((item) => (
                        <div key={item.document_id} className="rounded-2xl bg-white/80 p-4">
                          <div className="flex flex-wrap items-start justify-between gap-3">
                            <div>
                              <p className="font-semibold text-slate-900">{item.doc_name}</p>
                              <p className="text-sm text-slate-600">{item.filename}</p>
                            </div>
                            <StatusPill value={item.extraction_method} />
                          </div>
                          <p className="mt-3 text-xs uppercase tracking-[0.2em] text-slate-500">Text Preview</p>
                          <p className="mt-2 max-h-40 overflow-auto rounded-2xl bg-slate-50 p-3 text-sm leading-6 text-slate-700">
                            {item.text_preview || "No extractable text captured."}
                          </p>
                        </div>
                      ))
                    ) : (
                      <EmptyState title="No linked evidence" body="This criterion currently has no extracted evidence documents attached." />
                    )}
                  </div>
                </div>

                <div className="panel-muted p-5">
                  <p className="section-title">Extracted Values + Override Controls</p>
                  <div className="table-wrap mt-4">
                    <table>
                      <thead>
                        <tr>
                          <th>Field</th>
                          <th>Value</th>
                        </tr>
                      </thead>
                      <tbody>
                        {Object.entries(selectedEvent.extracted_values).map(([key, value]) => (
                          <tr key={key}>
                            <td className="font-semibold text-slate-900">{key}</td>
                            <td>{typeof value === "object" ? JSON.stringify(value) : String(value ?? "-")}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  {selectedEvent.hard_disqualification_flags.length ? (
                    <div className="mt-4 rounded-2xl bg-rose-50 p-4 text-sm text-rose-700">
                      <p className="font-semibold">Hard disqualification indicators</p>
                      <ul className="mt-2 space-y-2">
                        {selectedEvent.hard_disqualification_flags.map((flag) => (
                          <li key={flag}>{flag}</li>
                        ))}
                      </ul>
                    </div>
                  ) : null}

                  <div className="mt-5 grid gap-4 md:grid-cols-2">
                    <select className="field" value={finalVerdict} onChange={(event) => setFinalVerdict(event.target.value as typeof finalVerdict)}>
                      <option value="Eligible">Eligible</option>
                      <option value="Not Eligible">Not Eligible</option>
                      <option value="Needs Manual Review">Needs Manual Review</option>
                    </select>
                    <select className="field" value={reasonCode} onChange={(event) => setReasonCode(event.target.value)}>
                      {reasonCodes.map((code) => (
                        <option key={code} value={code}>
                          {code}
                        </option>
                      ))}
                    </select>
                  </div>
                  <textarea className="field mt-4 min-h-28" placeholder="Officer notes" value={reviewerNotes} onChange={(event) => setReviewerNotes(event.target.value)} />
                  <button className="button-primary mt-4" type="button" onClick={submitOverride}>
                    Record Override
                  </button>
                </div>
              </div>
            ) : null}
          </div>
        )}
      </Panel>
    </div>
  );
}
