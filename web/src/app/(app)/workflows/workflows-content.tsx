"use client";

import { useState } from "react";
import { useSearchParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { ScrollArea } from "@/components/ui/scroll-area";

export default function WorkflowsPageInner() {
  const params = useSearchParams();
  const selectedId = params.get("id");
  const [lastResult, setLastResult] = useState<unknown>(null);
  const qc = useQueryClient();

  const workflows = useQuery({ queryKey: ["workflows"], queryFn: api.workflows.list });
  const tasks = useQuery({ queryKey: ["tasks"], queryFn: api.tasks.list });
  const detail = useQuery({
    queryKey: ["workflow", selectedId],
    queryFn: () => api.workflows.get(selectedId!),
    enabled: !!selectedId,
  });

  const run = useMutation({
    mutationFn: (id: string) => api.workflows.run(id),
    onSuccess: (r) => {
      setLastResult(r);
      qc.invalidateQueries({ queryKey: ["tasks"] });
    },
  });

  const active = detail.data ?? workflows.data?.find((w) => w.workflow_id === selectedId);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Workflows</h1>
        <p className="text-sm text-muted-foreground">Run workflows and view execution history</p>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Installed</CardTitle>
          </CardHeader>
          <CardContent>
            {workflows.isLoading ? (
              <Skeleton className="h-32" />
            ) : (
              <ul className="space-y-2">
                {(workflows.data ?? []).map((w) => (
                  <li key={w.workflow_id} className="flex items-center justify-between gap-2">
                    <a
                      href={`/workflows?id=${w.workflow_id}`}
                      className="text-sm font-medium hover:underline"
                    >
                      {w.name}
                    </a>
                    <Button
                      size="sm"
                      onClick={() => run.mutate(w.workflow_id)}
                      disabled={run.isPending}
                    >
                      Run
                    </Button>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-base">
              {active ? active.name : "Workflow detail"}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {active ? (
              <ScrollArea className="h-[300px]">
                <pre className="text-xs">{JSON.stringify(active, null, 2)}</pre>
              </ScrollArea>
            ) : (
              <p className="text-sm text-muted-foreground">Select a workflow</p>
            )}
            {lastResult ? (
              <div className="mt-4 rounded-md border border-border p-3">
                <p className="text-sm font-medium">Last execution</p>
                <pre className="mt-2 text-xs">{JSON.stringify(lastResult, null, 2)}</pre>
              </div>
            ) : null}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Execution history</CardTitle>
        </CardHeader>
        <CardContent>
          <ul className="space-y-2 text-sm">
            {(tasks.data ?? []).map((t) => (
              <li key={t.task_id} className="flex items-center justify-between">
                <span>{t.workflow_id}</span>
                <Badge variant="outline">{t.status}</Badge>
              </li>
            ))}
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}
