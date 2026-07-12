"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";

function statusColor(status: string) {
  if (status === "healthy") return "default";
  if (status === "not_configured") return "secondary";
  return "outline";
}

export default function ProvidersPage() {
  const health = useQuery({ queryKey: ["provider-health"], queryFn: api.providers.health });
  const list = useQuery({ queryKey: ["providers"], queryFn: api.providers.list });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Providers</h1>
        <p className="text-sm text-muted-foreground">Configuration status and health</p>
      </div>

      {health.isLoading ? (
        <Skeleton className="h-40" />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {(health.data ?? []).map((p) => {
            const config = list.data?.find((c) => c.provider_id === p.provider_id);
            return (
              <Card key={p.provider_id}>
                <CardHeader className="pb-2">
                  <CardTitle className="flex items-center justify-between text-base">
                    {p.provider_id}
                    <Badge variant={statusColor(p.status)}>{p.status}</Badge>
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-2 text-sm">
                  <p className="text-muted-foreground">{p.message}</p>
                  {p.latency_ms != null && p.latency_ms > 0 && (
                    <p>Latency: {p.latency_ms}ms</p>
                  )}
                  {config && (
                    <div className="flex gap-2">
                      <Badge variant="outline">
                        {config.credentials_present ? "Configured" : "No credentials"}
                      </Badge>
                    </div>
                  )}
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
