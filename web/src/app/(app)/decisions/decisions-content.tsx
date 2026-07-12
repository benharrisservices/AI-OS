"use client";

import { useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { ScrollArea } from "@/components/ui/scroll-area";

export default function DecisionsPageInner() {
  const params = useSearchParams();
  const selectedId = params.get("id");

  const list = useQuery({ queryKey: ["decisions"], queryFn: api.decisions.list });
  const detail = useQuery({
    queryKey: ["decision", selectedId],
    queryFn: () => api.decisions.get(selectedId!),
    enabled: !!selectedId,
  });

  const active = detail.data ?? list.data?.find((d) => d.decision_id === selectedId);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Decisions</h1>
        <p className="text-sm text-muted-foreground">History, evidence, and reasoning traces</p>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle className="text-base">History</CardTitle>
          </CardHeader>
          <CardContent>
            {list.isLoading ? (
              <Skeleton className="h-40" />
            ) : !list.data?.length ? (
              <p className="text-sm text-muted-foreground">No decisions yet</p>
            ) : (
              <ul className="space-y-2">
                {list.data.map((d) => (
                  <li key={d.decision_id}>
                    <a
                      href={`/decisions?id=${d.decision_id}`}
                      className="block rounded-md p-2 text-sm hover:bg-muted"
                    >
                      <p className="line-clamp-2">{d.request.question}</p>
                      <div className="mt-1 flex gap-2">
                        <Badge variant="outline">{d.request.strategy}</Badge>
                        <span className="text-muted-foreground">
                          {(d.confidence * 100).toFixed(0)}%
                        </span>
                      </div>
                    </a>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-base">Detail</CardTitle>
          </CardHeader>
          <CardContent>
            {!active ? (
              <p className="text-sm text-muted-foreground">Select a decision</p>
            ) : (
              <ScrollArea className="h-[600px]">
                <div className="space-y-4 pr-4">
                  <div>
                    <h3 className="font-medium">{active.request.question}</h3>
                    <div className="mt-2 flex gap-2">
                      <Badge>{active.status}</Badge>
                      <Badge variant="outline">
                        Confidence {(active.confidence * 100).toFixed(0)}%
                      </Badge>
                    </div>
                  </div>
                  {active.recommendation && (
                    <div className="rounded-md border border-border p-3">
                      <p className="font-medium">{active.recommendation.title}</p>
                      <p className="mt-1 text-sm text-muted-foreground">
                        {active.recommendation.rationale}
                      </p>
                    </div>
                  )}
                  {active.evidence && active.evidence.length > 0 && (
                    <div>
                      <h4 className="text-sm font-medium">Evidence</h4>
                      <pre className="mt-2 text-xs">{JSON.stringify(active.evidence, null, 2)}</pre>
                    </div>
                  )}
                  {active.risks && active.risks.length > 0 && (
                    <div>
                      <h4 className="text-sm font-medium">Risks</h4>
                      <pre className="mt-2 text-xs">{JSON.stringify(active.risks, null, 2)}</pre>
                    </div>
                  )}
                  {active.reasoning_trace && (
                    <div>
                      <h4 className="text-sm font-medium">Reasoning trace</h4>
                      <pre className="mt-2 text-xs">
                        {JSON.stringify(active.reasoning_trace, null, 2)}
                      </pre>
                    </div>
                  )}
                </div>
              </ScrollArea>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
