"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { EmptyState, Panel, StatusPill } from "./components";
import { DashboardStats, Tender, getDashboardStats, getProfile, getTenders } from "./api-client";

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [tenders, setTenders] = useState<Tender[]>([]);
  const [profileName, setProfileName] = useState("Demo Officer");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([getDashboardStats(), getTenders(), getProfile()])
      .then(([statsPayload, tendersPayload, profile]) => {
        setStats(statsPayload);
        setTenders(tendersPayload);
        setProfileName(`${profile.full_name} (${profile.role})`);
      })
      .catch((err) => setError(err.message));
  }, []);

  return (
    <div className="space-y-6">
      <Panel
        title="Officer-first eligibility workbench"
        kicker="Mission"
        actions={<StatusPill value={profileName} />}
      >
        <div className="grid gap-5 lg:grid-cols-[1.4fr,1fr]">
          <div className="space-y-3 text-sm leading-7 text-slate-700">
            <p>
              PARAKH does not make opaque decisions. It assembles evidence, applies deterministic rules, and leaves a reviewable trail for every pass, fail, escalation, and override.
            </p>
            <p>
              The seeded demo account signs in automatically with the officer role, so you can move straight into tender setup, bidder ingestion, evaluation, and audit export.
            </p>
            <div className="flex flex-wrap gap-3 pt-2">
              <Link href="/tenders" className="button-primary">
                Open Tender Console
              </Link>
              <Link href="/tenders" className="button-secondary">
                Register a Bidder
              </Link>
            </div>
          </div>
          <div className="panel-muted p-5 text-sm text-slate-700">
            <p className="section-title">Operating Principle</p>
            <p className="mt-3 font-[var(--font-serif)] text-xl leading-8 text-slate-900">
              “The system’s job is not to make eligibility decisions. Its job is to make decisions transparent, consistent, and defensible.”
            </p>
          </div>
        </div>
      </Panel>

      {error ? <EmptyState title="Unable to load dashboard" body={error} /> : null}

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {[
          ["Tenders", stats?.tenders ?? 0],
          ["Bidders", stats?.bidders ?? 0],
          ["Disqualifications", stats?.disqualifications ?? 0],
          ["Auto Resolved", stats?.auto_resolved ?? 0],
          ["Overrides", stats?.manual_overrides ?? 0],
          ["Audit Events", stats?.evaluation_events ?? 0]
        ].map(([label, value]) => (
          <div key={String(label)} className="metric-card">
            <p className="section-title">{label}</p>
            <p className="mt-4 text-4xl font-semibold text-slate-950">{value}</p>
          </div>
        ))}
      </section>

      <Panel title="Active Tenders" kicker="Recent Activity">
        {tenders.length === 0 ? (
          <EmptyState title="No tenders yet" body="Create a tender to generate the eligibility manifest and start bidder assessments." />
        ) : (
          <div className="grid gap-4 md:grid-cols-2">
            {tenders.map((tender) => (
              <div key={tender._id} className="panel-muted p-5">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-lg font-semibold text-slate-900">{tender.title}</p>
                    <p className="mt-1 text-sm text-slate-600">{tender.procuring_entity}</p>
                    <p className="mt-3 text-xs uppercase tracking-[0.22em] text-slate-500">{tender.bid_reference}</p>
                  </div>
                  <StatusPill value={tender.status} />
                </div>
                <div className="mt-4 flex flex-wrap gap-2">
                  <Link href={`/tenders/${tender._id}`} className="button-secondary">
                    Manifest
                  </Link>
                  <Link href={`/tenders/${tender._id}/bidders`} className="button-secondary">
                    Bidders
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
