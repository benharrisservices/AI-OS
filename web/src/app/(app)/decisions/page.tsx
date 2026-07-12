"use client";

import { Suspense } from "react";
import DecisionsPageInner from "./decisions-content";

export default function DecisionsPage() {
  return (
    <Suspense fallback={<p className="text-sm text-muted-foreground">Loading…</p>}>
      <DecisionsPageInner />
    </Suspense>
  );
}
