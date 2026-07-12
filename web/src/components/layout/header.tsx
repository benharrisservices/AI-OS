"use client";

import { GlobalSearch } from "./global-search";

export function Header() {
  return (
    <header className="flex h-14 shrink-0 items-center gap-4 border-b border-border px-6">
      <GlobalSearch />
    </header>
  );
}
