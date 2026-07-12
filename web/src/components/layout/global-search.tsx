"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Search } from "lucide-react";
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from "@/components/ui/command";
import { api } from "@/lib/api";

export function GlobalSearch() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Awaited<
    ReturnType<typeof api.search.global>
  > | null>(null);
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === "k" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setOpen((o) => !o);
      }
    };
    document.addEventListener("keydown", down);
    return () => document.removeEventListener("keydown", down);
  }, []);

  useEffect(() => {
    if (!query || query.length < 2) {
      setResults(null);
      return;
    }
    const t = setTimeout(async () => {
      setLoading(true);
      try {
        const r = await api.search.global(query);
        setResults(r);
      } catch {
        setResults(null);
      } finally {
        setLoading(false);
      }
    }, 300);
    return () => clearTimeout(t);
  }, [query]);

  const go = useCallback(
    (href: string) => {
      setOpen(false);
      router.push(href);
    },
    [router],
  );

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="flex h-12 w-full max-w-lg items-center gap-2.5 rounded-2xl border border-border bg-muted/50 px-4 text-[1rem] font-medium text-muted-foreground transition-all duration-150 ease-out hover:border-primary/40 hover:bg-muted/70 hover:text-foreground"
        aria-label="Open search"
      >
        <Search className="h-[1.1875rem] w-[1.1875rem] shrink-0 opacity-80" strokeWidth={2.1} aria-hidden />
        <span className="flex-1 text-left">Search everything…</span>
        <kbd className="hidden items-center rounded-md border border-border/60 bg-foreground/[0.05] px-1.5 py-0.5 text-[0.75rem] font-semibold text-muted-foreground sm:inline-flex">
          ⌘K
        </kbd>
      </button>
      <CommandDialog open={open} onOpenChange={setOpen} title="Search sedr">
        <CommandInput
          placeholder="Knowledge, memory, decisions, workflows…"
          value={query}
          onValueChange={setQuery}
        />
        <CommandList>
          {loading && <CommandEmpty>Searching…</CommandEmpty>}
          {!loading && query.length >= 2 && !results && (
            <CommandEmpty>No results.</CommandEmpty>
          )}
          {results && results.knowledge.length > 0 && (
            <CommandGroup heading="Knowledge">
              {results.knowledge.slice(0, 5).map((h) => (
                <CommandItem
                  key={`${h.doc_id}-${h.chunk_id}`}
                  onSelect={() => go(`/knowledge?doc=${h.doc_id}`)}
                >
                  {h.title} — {h.excerpt.slice(0, 60)}
                </CommandItem>
              ))}
            </CommandGroup>
          )}
          {results && results.memories.length > 0 && (
            <>
              <CommandSeparator />
              <CommandGroup heading="Memory">
                {results.memories.slice(0, 5).map((m) => (
                  <CommandItem
                    key={m.memory_id}
                    onSelect={() => go(`/memory?id=${m.memory_id}`)}
                  >
                    {m.title || m.summary || m.memory_id}
                  </CommandItem>
                ))}
              </CommandGroup>
            </>
          )}
          {results && results.decisions.length > 0 && (
            <>
              <CommandSeparator />
              <CommandGroup heading="Decisions">
                {results.decisions.slice(0, 5).map((d) => (
                  <CommandItem
                    key={d.decision_id}
                    onSelect={() => go(`/decisions?id=${d.decision_id}`)}
                  >
                    {d.request.question.slice(0, 80)}
                  </CommandItem>
                ))}
              </CommandGroup>
            </>
          )}
          {results && results.workflows.length > 0 && (
            <>
              <CommandSeparator />
              <CommandGroup heading="Workflows">
                {results.workflows.map((w) => (
                  <CommandItem
                    key={w.workflow_id}
                    onSelect={() => go(`/workflows?id=${w.workflow_id}`)}
                  >
                    {w.name}
                  </CommandItem>
                ))}
              </CommandGroup>
            </>
          )}
        </CommandList>
      </CommandDialog>
    </>
  );
}
