"use client";

import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Skeleton } from "@/components/ui/skeleton";
import { ScrollArea } from "@/components/ui/scroll-area";

export default function KnowledgePage() {
  const [query, setQuery] = useState("");
  const [searchQ, setSearchQ] = useState("");
  const [selectedDoc, setSelectedDoc] = useState<string | null>(null);

  const status = useQuery({ queryKey: ["knowledge-status"], queryFn: api.knowledge.status });
  const documents = useQuery({ queryKey: ["knowledge-docs"], queryFn: api.knowledge.documents });
  const sources = useQuery({ queryKey: ["knowledge-sources"], queryFn: api.knowledge.sources });
  const search = useQuery({
    queryKey: ["knowledge-search", searchQ],
    queryFn: () => api.knowledge.search(searchQ),
    enabled: searchQ.length >= 2,
  });
  const docDetail = useQuery({
    queryKey: ["knowledge-doc", selectedDoc],
    queryFn: () => api.knowledge.document(selectedDoc!),
    enabled: !!selectedDoc,
  });
  const retrieve = useMutation({
    mutationFn: (q: string) => api.knowledge.retrieve(q),
  });
  const reindex = useMutation({
    mutationFn: () => api.knowledge.reindex(),
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="page-title">Knowledge</h1>
        <p className="page-subtitle">
          Search, browse sources, and inspect documents
        </p>
      </div>

      {status.data && (
        <div className="flex flex-wrap gap-2">
          <Badge variant={status.data.healthy ? "default" : "secondary"}>
            {status.data.healthy ? "Healthy" : "Needs attention"}
          </Badge>
          <Badge variant="outline">{status.data.document_count} documents</Badge>
          <Badge variant="outline">{status.data.chunk_count} chunks</Badge>
          <Badge variant="outline">{status.data.source_count} sources</Badge>
          <Button size="sm" variant="outline" onClick={() => reindex.mutate()} disabled={reindex.isPending}>
            Reindex
          </Button>
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Search</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
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
              placeholder="Search knowledge base…"
              aria-label="Search knowledge"
            />
            <Button type="submit">Search</Button>
            <Button
              type="button"
              variant="secondary"
              onClick={() => retrieve.mutate(query)}
              disabled={!query || retrieve.isPending}
            >
              Retrieve
            </Button>
          </form>
          {search.isLoading && <Skeleton className="h-20" />}
          {search.data && (
            <ul className="space-y-2">
              {search.data.map((h, i) => (
                <li
                  key={`${h.doc_id}-${i}`}
                  className="cursor-pointer rounded-md border border-border p-3 text-sm hover:bg-muted/50"
                  onClick={() => setSelectedDoc(h.doc_id)}
                >
                  <div className="flex justify-between">
                    <span className="font-medium">{h.title}</span>
                    <span className="text-muted-foreground">{h.score.toFixed(3)}</span>
                  </div>
                  <p className="mt-1 text-muted-foreground">{h.excerpt}</p>
                </li>
              ))}
            </ul>
          )}
          {retrieve.data != null ? (
            <pre className="max-h-48 overflow-auto rounded-md bg-muted p-3 text-xs">
              {JSON.stringify(retrieve.data, null, 2)}
            </pre>
          ) : null}
        </CardContent>
      </Card>

      <Tabs defaultValue="documents">
        <TabsList>
          <TabsTrigger value="documents">Documents</TabsTrigger>
          <TabsTrigger value="sources">Sources</TabsTrigger>
          <TabsTrigger value="viewer">Viewer</TabsTrigger>
        </TabsList>
        <TabsContent value="documents">
          <Card>
            <CardContent className="pt-6">
              {documents.isLoading ? (
                <Skeleton className="h-40" />
              ) : (
                <ScrollArea className="h-[400px]">
                  <ul className="space-y-1">
                    {(documents.data ?? []).map((d) => (
                      <li key={d.doc_id}>
                        <button
                          type="button"
                          className="w-full rounded px-2 py-1.5 text-left text-sm hover:bg-muted"
                          onClick={() => setSelectedDoc(d.doc_id)}
                        >
                          {d.title}
                        </button>
                      </li>
                    ))}
                  </ul>
                </ScrollArea>
              )}
            </CardContent>
          </Card>
        </TabsContent>
        <TabsContent value="sources">
          <Card>
            <CardContent className="pt-6">
              <ul className="space-y-2 text-sm">
                {(sources.data ?? []).map((s) => (
                  <li key={s.source_id} className="rounded border border-border p-2">
                    <p className="font-medium">{s.title || s.source_id}</p>
                    <p className="truncate text-muted-foreground">{s.original_uri}</p>
                    <Badge variant="outline" className="mt-1">{s.status}</Badge>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>
        </TabsContent>
        <TabsContent value="viewer">
          <Card>
            <CardContent className="pt-6">
              {!selectedDoc ? (
                <p className="text-sm text-muted-foreground">Select a document</p>
              ) : docDetail.isLoading ? (
                <Skeleton className="h-40" />
              ) : (
                <ScrollArea className="h-[500px]">
                  <pre className="text-xs">{JSON.stringify(docDetail.data, null, 2)}</pre>
                </ScrollArea>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
