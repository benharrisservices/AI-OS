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
        className="flex h-9 w-full max-w-md items-center gap-2 rounded-lg border border-border bg-muted/40 px-3 text-sm text-muted-foreground transition-colors hover:bg-muted/60"
        aria-label="Open search"
      >
        <Search className="h-4 w-4 shrink-0" aria-hidden />
        <span className="flex-1 text-left">Search everything…</span>
        <kbd className="hidden rounded border border-border bg-background px-1.5 py-0.5 text-[10px] font-medium sm:inline">
          ⌘K
        </kbd>
      </button>
      <CommandDialog open={open} onOpenChange={setOpen} title="Search Sedr">
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
