"use client";

import { useEffect, useMemo, useState } from "react";

import { AuditHistory, downloadAuditReport, getAuditHistory } from "../../../api-client";
import { EmptyState, Panel, StatusPill, formatDate } from "../../../components";

export default function AuditPage({ params }: { params: { tender_id: string; bidder_id: string } }) {
  const { tender_id: tenderId, bidder_id: bidderId } = params;
  const [history, setHistory] = useState<AuditHistory>({});
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getAuditHistory(tenderId, bidderId)
      .then(setHistory)
      .catch((err) => setError(err.message));
  }, [bidderId, tenderId]);

  const totalEvents = useMemo(
    () => Object.values(history).reduce((sum, events) => sum + events.length, 0),
    [history]
  );

  return (
    <Panel
      title="Audit Timeline"
      kicker="Immutable Event Ledger"
      actions={
        <div className="flex flex-wrap gap-2">
          <button className="button-secondary" type="button" onClick={() => downloadAuditReport(tenderId, bidderId, "xlsx")}>
            Export Excel
          </button>
          <button className="button-primary" type="button" onClick={() => downloadAuditReport(tenderId, bidderId, "pdf")}>
            Export PDF
          </button>
        </div>
      }
    >
      {error ? <p className="mb-4 text-sm text-rose-700">{error}</p> : null}

      {!Object.keys(history).length ? (
        <EmptyState title="No audit history yet" body="Run evaluation first to create append-only audit events." />
      ) : (
        <div className="space-y-6">
          <div className="panel-muted p-4 text-sm text-slate-700">
            <p>
              Total audit events: <span className="font-semibold text-slate-900">{totalEvents}</span>
            </p>
          </div>

          {Object.entries(history).map(([criterionName, events]) => (
            <div key={criterionName} className="panel-muted p-5">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="section-title">{events[0]?.stage}</p>
                  <p className="mt-2 text-xl font-semibold text-slate-900">{criterionName}</p>
                </div>
                <StatusPill value={events[events.length - 1]?.final_verdict ?? "Needs Manual Review"} />
              </div>

              <div className="mt-5 space-y-4">
                {events.map((event) => (
                  <div key={event._id} className="rounded-2xl border border-slate-200 bg-white/80 p-4">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div>
                        <p className="font-semibold text-slate-900">
                          {event.event_type} · Seq {event.sequence}
                        </p>
                        <p className="mt-1 text-sm text-slate-600">{formatDate(event.created_at)}</p>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        <StatusPill value={event.auto_verdict} />
                        <StatusPill value={event.final_verdict} />
                      </div>
                    </div>
                    <p className="mt-4 text-sm leading-7 text-slate-700">{event.match_logic}</p>
                    <div className="mt-4 grid gap-3 md:grid-cols-2">
                      <div className="rounded-2xl bg-slate-50 p-3 text-sm text-slate-700">
                        <p className="font-semibold text-slate-900">Evidence Docs</p>
                        <ul className="mt-2 space-y-2">
                          {event.evidence_docs.length ? event.evidence_docs.map((doc) => <li key={doc.document_id}>{doc.doc_name} ({doc.filename})</li>) : <li>-</li>}
                        </ul>
                      </div>
                      <div className="rounded-2xl bg-slate-50 p-3 text-sm text-slate-700">
                        <p className="font-semibold text-slate-900">Chain Metadata</p>
                        <p className="mt-2 break-all text-xs">hash: {event.event_hash}</p>
                        <p className="mt-2 break-all text-xs">prior: {event.prior_event_id || "origin"}</p>
                      </div>
                    </div>
                    {event.reason_code ? <p className="mt-4 text-sm text-slate-600">Reason code: {event.reason_code}</p> : null}
                    {event.reviewer_notes ? <p className="mt-2 text-sm text-slate-600">Notes: {event.reviewer_notes}</p> : null}
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </Panel>
  );
}
