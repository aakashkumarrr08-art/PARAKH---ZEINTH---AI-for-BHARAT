"use client";

import { ReactNode } from "react";

export function StatusPill({ value }: { value: string }) {
  const palette =
    value === "Eligible" || value === "OK"
      ? "bg-emerald-100 text-emerald-800"
      : value === "Not Eligible" || value === "DISQUALIFIED"
        ? "bg-rose-100 text-rose-800"
        : value === "APPROVED"
          ? "bg-sky-100 text-sky-800"
          : "bg-amber-100 text-amber-800";

  return <span className={`chip ${palette}`}>{value}</span>;
}

export function Panel({
  title,
  kicker,
  children,
  actions
}: {
  title: string;
  kicker?: string;
  children: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <section className="panel p-6">
      <div className="mb-5 flex flex-wrap items-start justify-between gap-3">
        <div>
          {kicker ? <p className="section-title">{kicker}</p> : null}
          <h2 className="mt-2 text-xl font-semibold text-slate-900">{title}</h2>
        </div>
        {actions}
      </div>
      {children}
    </section>
  );
}

export function EmptyState({ title, body }: { title: string; body: string }) {
  return (
    <div className="panel-muted p-6 text-sm text-slate-600">
      <p className="font-semibold text-slate-900">{title}</p>
      <p className="mt-2">{body}</p>
    </div>
  );
}

export function formatDate(value?: string | null) {
  if (!value) return "Not set";
  try {
    return new Date(value).toLocaleString();
  } catch {
    return value;
  }
}
