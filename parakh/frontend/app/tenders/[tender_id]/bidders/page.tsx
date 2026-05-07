"use client";

import Link from "next/link";
import { FormEvent, useEffect, useMemo, useState } from "react";

import { Bidder, ChecklistItem, createBidder, evaluateBidder, getBidderChecklist, getBidders, ingestBidderDocs, uploadBidderDocument } from "../../../api-client";
import { EmptyState, Panel, StatusPill } from "../../../components";

const initialBidderForm = {
  name: "",
  bidder_type: "AUTHORIZED_BIDDER" as "OEM" | "AUTHORIZED_BIDDER",
  oem_name: ""
};

export default function TenderBiddersPage({ params }: { params: { tender_id: string } }) {
  const tenderId = params.tender_id;
  const [bidders, setBidders] = useState<Bidder[]>([]);
  const [selectedBidderId, setSelectedBidderId] = useState<string>("");
  const [checklist, setChecklist] = useState<ChecklistItem[]>([]);
  const [form, setForm] = useState(initialBidderForm);
  const [files, setFiles] = useState<Record<string, File | null>>({});
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const selectedBidder = useMemo(
    () => bidders.find((bidder) => bidder._id === selectedBidderId) ?? null,
    [bidders, selectedBidderId]
  );

  useEffect(() => {
    getBidders(tenderId)
      .then((payload) => {
        setBidders(payload);
        if (payload[0]) {
          setSelectedBidderId(payload[0]._id);
        }
      })
      .catch((err) => setError(err.message));
  }, [tenderId]);

  useEffect(() => {
    if (!selectedBidderId) {
      setChecklist([]);
      return;
    }
    getBidderChecklist(tenderId, selectedBidderId)
      .then(setChecklist)
      .catch((err) => setError(err.message));
  }, [selectedBidderId, tenderId]);

  async function handleCreateBidder(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    try {
      const bidder = await createBidder(tenderId, form);
      setBidders((current) => [bidder, ...current]);
      setSelectedBidderId(bidder._id);
      setForm(initialBidderForm);
      setMessage("Bidder registered. You can upload checklist documents on the right.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create bidder.");
    }
  }

  async function handleUpload(docName: string) {
    const file = files[docName];
    if (!selectedBidderId || !file) return;
    try {
      const updatedBidder = await uploadBidderDocument(tenderId, selectedBidderId, docName, file);
      setBidders((current) => current.map((bidder) => (bidder._id === updatedBidder._id ? updatedBidder : bidder)));
      setChecklist(updatedBidder.checklist_status);
      setFiles((current) => ({ ...current, [docName]: null }));
      setMessage(`${docName} uploaded.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed.");
    }
  }

  async function handleIngest() {
    if (!selectedBidderId) return;
    try {
      await ingestBidderDocs(tenderId, selectedBidderId);
      setMessage("Bidder documents ingested. Extracted evidence is ready for evaluation.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ingestion failed.");
    }
  }

  async function handleEvaluate() {
    if (!selectedBidderId) return;
    try {
      const overview = await evaluateBidder(tenderId, selectedBidderId);
      setBidders((current) =>
        current.map((bidder) =>
          bidder._id === selectedBidderId
            ? {
                ...bidder,
                overall_status: overview.overall_status,
                hard_disqualified: overview.hard_disqualified,
                disqualification_reasons: overview.disqualification_reasons
              }
            : bidder
        )
      );
      setMessage("Evaluation completed. Open the workbench for criterion-level review and overrides.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Evaluation failed.");
    }
  }

  return (
    <div className="grid gap-6 xl:grid-cols-[0.88fr,1.4fr]">
      <Panel title="Register Bidder" kicker="BDI Intake">
        <form className="space-y-4" onSubmit={handleCreateBidder}>
          <input className="field" placeholder="Bidder name" value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} required />
          <select className="field" value={form.bidder_type} onChange={(event) => setForm({ ...form, bidder_type: event.target.value as "OEM" | "AUTHORIZED_BIDDER" })}>
            <option value="AUTHORIZED_BIDDER">Authorized Bidder</option>
            <option value="OEM">OEM</option>
          </select>
          <input className="field" placeholder="OEM name (optional)" value={form.oem_name} onChange={(event) => setForm({ ...form, oem_name: event.target.value })} />
          <button className="button-primary" type="submit">
            Register Bidder
          </button>
        </form>

        <div className="mt-6 space-y-3">
          {bidders.map((bidder) => (
            <button
              key={bidder._id}
              type="button"
              onClick={() => setSelectedBidderId(bidder._id)}
              className={`w-full rounded-3xl border p-4 text-left transition ${selectedBidderId === bidder._id ? "border-amber-400 bg-amber-50" : "border-slate-200 bg-white/70"}`}
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="font-semibold text-slate-900">{bidder.name}</p>
                  <p className="mt-1 text-sm text-slate-600">{bidder.bidder_type}</p>
                </div>
                <StatusPill value={bidder.overall_status} />
              </div>
              {bidder.hard_disqualified ? <p className="mt-3 text-sm text-rose-700">Hard disqualification flagged</p> : null}
            </button>
          ))}
          {!bidders.length ? <EmptyState title="No bidders yet" body="Register a bidder to unlock the document checklist and ingestion flow." /> : null}
        </div>
      </Panel>

      <Panel
        title={selectedBidder ? `${selectedBidder.name} Submission Checklist` : "Bidder Checklist"}
        kicker="Checklist-driven Upload"
        actions={
          selectedBidder ? (
            <div className="flex flex-wrap gap-2">
              <button className="button-secondary" type="button" onClick={handleIngest}>
                Ingest Documents
              </button>
              <button className="button-primary" type="button" onClick={handleEvaluate}>
                Evaluate Bidder
              </button>
            </div>
          ) : null
        }
      >
        {message ? <p className="mb-4 text-sm text-emerald-700">{message}</p> : null}
        {error ? <p className="mb-4 text-sm text-rose-700">{error}</p> : null}

        {!selectedBidder ? (
          <EmptyState title="Pick a bidder" body="Choose a bidder from the left to upload the document checklist, ingest evidence, and launch evaluation." />
        ) : (
          <div className="space-y-5">
            <div className="flex flex-wrap gap-3">
              <StatusPill value={selectedBidder.overall_status} />
              {selectedBidder.hard_disqualified ? <StatusPill value="DISQUALIFIED" /> : null}
              <Link href={`/evaluation/${tenderId}/${selectedBidder._id}`} className="button-secondary">
                Open Workbench
              </Link>
              <Link href={`/audit/${tenderId}/${selectedBidder._id}`} className="button-secondary">
                Open Audit
              </Link>
            </div>

            {selectedBidder.disqualification_reasons.length ? (
              <div className="rounded-2xl bg-rose-50 p-4 text-sm text-rose-700">
                <p className="font-semibold">Current disqualification reasons</p>
                <ul className="mt-2 space-y-2">
                  {selectedBidder.disqualification_reasons.map((reason) => (
                    <li key={reason}>{reason}</li>
                  ))}
                </ul>
              </div>
            ) : null}

            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Document</th>
                    <th>Description</th>
                    <th>Status</th>
                    <th>Upload</th>
                  </tr>
                </thead>
                <tbody>
                  {checklist.map((item) => (
                    <tr key={item.doc_name}>
                      <td className="w-[18%] font-semibold text-slate-900">{item.doc_name}</td>
                      <td className="w-[42%]">
                        <p>{item.doc_description}</p>
                        <p className="mt-2 text-xs text-slate-500">{item.doc_purpose}</p>
                      </td>
                      <td className="w-[15%]">
                        {item.uploaded ? (
                          <div className="space-y-1">
                            <StatusPill value="Uploaded" />
                            <p className="text-xs text-slate-500">{item.filename}</p>
                          </div>
                        ) : (
                          <StatusPill value="Pending" />
                        )}
                      </td>
                      <td className="w-[25%]">
                        <div className="space-y-2">
                          <input className="field" type="file" onChange={(event) => setFiles((current) => ({ ...current, [item.doc_name]: event.target.files?.[0] ?? null }))} />
                          <button className="button-secondary w-full" type="button" onClick={() => handleUpload(item.doc_name)}>
                            Upload {item.doc_name}
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </Panel>
    </div>
  );
}
