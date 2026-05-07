"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";

import { EmptyState, Panel, StatusPill } from "../components";
import { Tender, createTender, getTenders } from "../api-client";

const initialForm = {
  title: "",
  procuring_entity: "Central Reserve Police Force",
  bid_reference: "",
  description: "",
  bid_validity_end: ""
};

export default function TenderListPage() {
  const [tenders, setTenders] = useState<Tender[]>([]);
  const [form, setForm] = useState(initialForm);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getTenders().then(setTenders).catch((err) => setError(err.message));
  }, []);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    try {
      const tender = await createTender({
        ...form,
        description: form.description || undefined,
        bid_validity_end: form.bid_validity_end || undefined
      });
      setTenders((current) => [tender, ...current]);
      setForm(initialForm);
      setMessage("Tender created. You can upload tender docs and generate a draft manifest now.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create tender.");
    }
  }

  return (
    <div className="grid gap-6 xl:grid-cols-[1.1fr,1.4fr]">
      <Panel title="Create Tender" kicker="Authority Intake">
        <form className="space-y-4" onSubmit={handleSubmit}>
          <input className="field" placeholder="Tender title" value={form.title} onChange={(event) => setForm({ ...form, title: event.target.value })} required />
          <input className="field" placeholder="Procuring entity" value={form.procuring_entity} onChange={(event) => setForm({ ...form, procuring_entity: event.target.value })} required />
          <input className="field" placeholder="Bid reference" value={form.bid_reference} onChange={(event) => setForm({ ...form, bid_reference: event.target.value })} required />
          <textarea className="field min-h-28" placeholder="Short description" value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })} />
          <input className="field" type="date" value={form.bid_validity_end} onChange={(event) => setForm({ ...form, bid_validity_end: event.target.value })} />
          <button className="button-primary" type="submit">
            Create Tender
          </button>
        </form>
        {message ? <p className="mt-4 text-sm text-emerald-700">{message}</p> : null}
        {error ? <p className="mt-4 text-sm text-rose-700">{error}</p> : null}
      </Panel>

      <Panel title="Tender Portfolio" kicker="Procurement Pipeline">
        {tenders.length === 0 ? (
          <EmptyState title="No tenders available" body="Create a tender on the left to start generating criteria manifests and bidder workspaces." />
        ) : (
          <div className="grid gap-4">
            {tenders.map((tender) => (
              <div key={tender._id} className="panel-muted p-5">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="text-lg font-semibold text-slate-900">{tender.title}</p>
                    <p className="mt-1 text-sm text-slate-600">{tender.procuring_entity}</p>
                    <p className="mt-2 text-xs uppercase tracking-[0.24em] text-slate-500">{tender.bid_reference}</p>
                  </div>
                  <StatusPill value={tender.status} />
                </div>
                <p className="mt-4 text-sm leading-6 text-slate-700">{tender.description || "No description provided."}</p>
                <div className="mt-4 flex flex-wrap gap-2">
                  <Link href={`/tenders/${tender._id}`} className="button-secondary">
                    Manage Manifest
                  </Link>
                  <Link href={`/tenders/${tender._id}/bidders`} className="button-primary">
                    Open Bidders
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}
      </Panel>
    </div>
  );
}
