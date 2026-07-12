"use client";

import { Suspense } from "react";
import WorkflowsPageInner from "./workflows-content";

export default function WorkflowsPage() {
  return (
    <Suspense fallback={<p className="text-sm text-muted-foreground">Loading…</p>}>
      <WorkflowsPageInner />
    </Suspense>
  );
}
