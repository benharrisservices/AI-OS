"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Skeleton } from "@/components/ui/skeleton";

const MEMORY_TYPES = ["working", "episodic", "semantic", "procedural"];

export default function MemoryPage() {
  const [query, setQuery] = useState("");
  const [searchQ, setSearchQ] = useState("");
  const [typeFilter, setTypeFilter] = useState<string | undefined>();

  const list = useQuery({
    queryKey: ["memory-list", typeFilter],
    queryFn: () => api.memory.list(typeFilter),
  });
  const search = useQuery({
    queryKey: ["memory-search", searchQ],
    queryFn: () => api.memory.search(searchQ),
    enabled: searchQ.length >= 1,
  });
  const insights = useQuery({ queryKey: ["memory-insights"], queryFn: api.memory.insights });
  const timeline = useQuery({ queryKey: ["memory-timeline"], queryFn: () => api.memory.timeline() });

  const records = searchQ ? search.data : list.data;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Memory</h1>
        <p className="text-sm text-muted-foreground">Timeline, tiers, and intelligence</p>
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          setSearchQ(query);
        }}
        className="flex gap-2"
      >
        <Input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search memories…"
          aria-label="Search memories"
        />
        <Button type="submit">Search</Button>
      </form>

      <div className="flex flex-wrap gap-2">
        <Button
          size="sm"
          variant={!typeFilter ? "default" : "outline"}
          onClick={() => setTypeFilter(undefined)}
        >
          All
        </Button>
        {MEMORY_TYPES.map((t) => (
          <Button
            key={t}
            size="sm"
            variant={typeFilter === t ? "default" : "outline"}
            onClick={() => setTypeFilter(t)}
          >
            {t}
          </Button>
        ))}
      </div>

      <Tabs defaultValue="list">
        <TabsList>
          <TabsTrigger value="list">Memories</TabsTrigger>
          <TabsTrigger value="timeline">Timeline</TabsTrigger>
          <TabsTrigger value="insights">Insights</TabsTrigger>
        </TabsList>
        <TabsContent value="list">
          <Card>
            <CardContent className="pt-6">
              {list.isLoading ? (
                <Skeleton className="h-40" />
              ) : !records?.length ? (
                <p className="text-sm text-muted-foreground">No memories found</p>
              ) : (
                <ul className="space-y-2">
                  {records.map((m) => (
                    <li key={m.memory_id} className="rounded-md border border-border p-3 text-sm">
                      <div className="flex items-center gap-2">
                        <Badge variant="outline">{m.memory_type}</Badge>
                        <span className="font-medium">{m.title || m.memory_id}</span>
                      </div>
                      {m.summary && (
                        <p className="mt-1 text-muted-foreground">{m.summary}</p>
                      )}
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>
        </TabsContent>
        <TabsContent value="timeline">
          <Card>
            <CardContent className="pt-6">
              <ul className="space-y-2 text-sm">
                {(timeline.data ?? []).map((e, i) => (
                  <li key={i} className="flex gap-3">
                    <span className="text-muted-foreground">{e.occurred_at}</span>
                    <Badge variant="outline">{e.event_type}</Badge>
                    <span>{e.title}</span>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>
        </TabsContent>
        <TabsContent value="insights">
          <div className="grid gap-4 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Duplicates</CardTitle>
              </CardHeader>
              <CardContent className="text-sm text-muted-foreground">
                {insights.data?.duplicates.length ?? 0} groups
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Semantic clusters</CardTitle>
              </CardHeader>
              <CardContent className="text-sm">
                {Object.keys(insights.data?.clusters ?? {}).length} clusters
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Promotion candidates</CardTitle>
              </CardHeader>
              <CardContent className="text-sm">
                {insights.data?.promotions.length ?? 0} recommended
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Relationship graph</CardTitle>
              </CardHeader>
              <CardContent>
                <pre className="max-h-32 overflow-auto text-xs">
                  {JSON.stringify(insights.data?.graph ?? {}, null, 2)}
                </pre>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
