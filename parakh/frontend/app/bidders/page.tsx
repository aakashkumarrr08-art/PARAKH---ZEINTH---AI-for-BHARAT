import Link from "next/link";

import { EmptyState, Panel } from "../components";

export default function BidderHubPage() {
  return (
    <Panel title="Bidder Hub" kicker="Guidance">
      <EmptyState
        title="Bidder workspaces are tender-scoped"
        body="Open a tender first, then use its bidder console to register firms, upload checklist documents, ingest evidence, and launch evaluations."
      />
      <div className="mt-4">
        <Link href="/tenders" className="button-primary">
          Go to Tenders
        </Link>
      </div>
    </Panel>
  );
}
