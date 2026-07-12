"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Activity,
  BookOpen,
  Brain,
  Cpu,
  Play,
  Plug,
  Scale,
  Stethoscope,
  Sun,
} from "lucide-react";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import Link from "next/link";

function formatBytes(n: number) {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

export default function DashboardPage() {
  const qc = useQueryClient();
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["dashboard"],
    queryFn: api.dashboard,
    refetchInterval: 60_000,
  });

  const runWorkflow = useMutation({
    mutationFn: (id: string) => api.workflows.run(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["dashboard"] }),
  });

  const doctor = useMutation({
    mutationFn: () => api.settings.doctor(),
  });

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-48" />
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-28" />
          ))}
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-6">
        <p className="font-medium text-destructive">Cannot reach Sedr API</p>
        <p className="mt-1 text-sm text-muted-foreground">
          Start the API: <code className="text-xs">uv run ai-os-api</code>
        </p>
        <Button variant="outline" className="mt-4" onClick={() => refetch()}>
          Retry
        </Button>
      </div>
    );
  }

  const healthyProviders = data.provider_health.filter(
    (p) => p.status === "healthy",
  ).length;

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Dashboard</h1>
          <p className="text-sm text-muted-foreground">
            System overview ·{" "}
            <Badge variant={data.status === "healthy" ? "default" : "secondary"}>
              {data.status}
            </Badge>
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button
            size="sm"
            onClick={() => runWorkflow.mutate("morning-briefing")}
            disabled={runWorkflow.isPending}
          >
            <Sun className="mr-1.5 h-4 w-4" aria-hidden />
            Morning Briefing
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={() => doctor.mutate()}
            disabled={doctor.isPending}
          >
            <Stethoscope className="mr-1.5 h-4 w-4" aria-hidden />
            System Doctor
          </Button>
        </div>
      </div>

      <section aria-labelledby="stats-heading">
        <h2 id="stats-heading" className="sr-only">
          Statistics
        </h2>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Knowledge
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-semibold">{data.counts.documents}</p>
              <p className="text-xs text-muted-foreground">
                {data.counts.chunks} chunks · {formatBytes(data.health.storage_bytes)}
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Memories
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-semibold">{data.counts.memories}</p>
              <p className="text-xs text-muted-foreground">
                {data.counts.automations} automations
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Providers
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-semibold">
                {healthyProviders}/{data.counts.providers}
              </p>
              <p className="text-xs text-muted-foreground">healthy</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Model Router
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-lg font-semibold">
                {data.model_route.provider_id}/{data.model_route.model_id}
              </p>
              <p className="text-xs text-muted-foreground">
                score {data.model_route.score.toFixed(2)}
              </p>
            </CardContent>
          </Card>
        </div>
      </section>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Activity className="h-4 w-4" aria-hidden />
              Recent Activity
            </CardTitle>
          </CardHeader>
          <CardContent>
            {data.recent_activity.length === 0 ? (
              <p className="text-sm text-muted-foreground">No recent activity</p>
            ) : (
              <ul className="space-y-2">
                {data.recent_activity.map((a) => (
                  <li
                    key={a.execution_id}
                    className="flex items-center justify-between text-sm"
                  >
                    <span>{a.automation_id}</span>
                    <Badge variant="outline">{a.status}</Badge>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Scale className="h-4 w-4" aria-hidden />
              Recent Decisions
            </CardTitle>
          </CardHeader>
          <CardContent>
            {data.recent_decisions.length === 0 ? (
              <p className="text-sm text-muted-foreground">No decisions yet</p>
            ) : (
              <ul className="space-y-2">
                {data.recent_decisions.map((d) => (
                  <li key={d.decision_id}>
                    <Link
                      href={`/decisions?id=${d.decision_id}`}
                      className="text-sm hover:underline"
                    >
                      {d.request.question.slice(0, 80)}
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Brain className="h-4 w-4" aria-hidden />
              Recent Memories
            </CardTitle>
          </CardHeader>
          <CardContent>
            {data.recent_memories.length === 0 ? (
              <p className="text-sm text-muted-foreground">No memories</p>
            ) : (
              <ul className="space-y-2 text-sm">
                {data.recent_memories.map((m) => (
                  <li key={m.memory_id}>
                    [{m.memory_type}] {m.title || m.summary || m.memory_id}
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <BookOpen className="h-4 w-4" aria-hidden />
              Recent Knowledge
            </CardTitle>
          </CardHeader>
          <CardContent>
            {data.recent_knowledge.length === 0 ? (
              <p className="text-sm text-muted-foreground">No knowledge hits</p>
            ) : (
              <ul className="space-y-2 text-sm">
                {data.recent_knowledge.map((k, i) => (
                  <li key={`${k.doc_id}-${i}`}>{k.title}</li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Plug className="h-4 w-4" aria-hidden />
            Provider Health
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-2">
            {data.provider_health.map((p) => (
              <Badge
                key={p.provider_id}
                variant={p.status === "healthy" ? "default" : "secondary"}
              >
                {p.provider_id}: {p.status}
                {p.latency_ms ? ` (${p.latency_ms}ms)` : ""}
              </Badge>
            ))}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Play className="h-4 w-4" aria-hidden />
            Quick Actions
          </CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          {data.workflows.slice(0, 6).map((w) => (
            <Button
              key={w.workflow_id}
              size="sm"
              variant="outline"
              onClick={() => runWorkflow.mutate(w.workflow_id)}
              disabled={runWorkflow.isPending}
            >
              {w.name}
            </Button>
          ))}
          <Link
            href="/providers"
            className="inline-flex h-8 items-center justify-center rounded-lg px-2.5 text-xs font-medium hover:bg-muted"
          >
            <Plug className="mr-1 h-3 w-3" /> Provider Health
          </Link>
          <Link
            href="/models"
            className="inline-flex h-8 items-center justify-center rounded-lg px-2.5 text-xs font-medium hover:bg-muted"
          >
            <Cpu className="mr-1 h-3 w-3" /> Model Router
          </Link>
        </CardContent>
      </Card>
    </div>
  );
}
