"use client";

import { GlobalSearch } from "./global-search";
import { ThemeToggle } from "@/components/theme/theme-toggle";

export function Header() {
  return (
    <header className="flex h-[3.5rem] shrink-0 items-center gap-4 border-b border-border/70 px-7">
      <GlobalSearch />
      <div className="ml-auto shrink-0">
        <ThemeToggle />
      </div>
    </header>
  );
}
