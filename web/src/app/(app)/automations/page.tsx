"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { Skeleton } from "@/components/ui/skeleton";

export default function AutomationsPage() {
  const qc = useQueryClient();
  const list = useQuery({ queryKey: ["automations"], queryFn: api.automations.list });
  const history = useQuery({
    queryKey: ["automation-history"],
    queryFn: () => api.automations.history(30),
  });

  const run = useMutation({
    mutationFn: (id: string) => api.automations.run(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["automation-history"] }),
  });
  const enable = useMutation({
    mutationFn: (id: string) => api.automations.enable(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["automations"] }),
  });
  const disable = useMutation({
    mutationFn: (id: string) => api.automations.disable(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["automations"] }),
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Automations</h1>
        <p className="text-sm text-muted-foreground">Scheduled jobs and trigger history</p>
      </div>

      {list.isLoading ? (
        <Skeleton className="h-40" />
      ) : (
        <div className="grid gap-4">
          {(list.data ?? []).map((a) => (
            <Card key={a.automation_id}>
              <CardContent className="flex flex-wrap items-center justify-between gap-4 pt-6">
                <div>
                  <p className="font-medium">{a.name}</p>
                  <p className="text-sm text-muted-foreground">{a.description}</p>
                  <Badge variant="outline" className="mt-2">
                    {a.status}
                  </Badge>
                </div>
                <div className="flex items-center gap-3">
                  <Switch
                    checked={a.status === "enabled"}
                    onCheckedChange={(on) =>
                      on ? enable.mutate(a.automation_id) : disable.mutate(a.automation_id)
                    }
                    aria-label={`Toggle ${a.name}`}
                  />
                  <Button
                    size="sm"
                    onClick={() => run.mutate(a.automation_id)}
                    disabled={run.isPending}
                  >
                    Run now
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Trigger history</CardTitle>
        </CardHeader>
        <CardContent>
          <ul className="space-y-2 text-sm">
            {(history.data ?? []).map((h) => (
              <li key={h.execution_id} className="flex justify-between">
                <span>{h.automation_id}</span>
                <div className="flex gap-2">
                  <Badge variant="outline">{h.status}</Badge>
                  {h.duration_ms != null && (
                    <span className="text-muted-foreground">{h.duration_ms}ms</span>
                  )}
                </div>
              </li>
            ))}
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}
