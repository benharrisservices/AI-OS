"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";

import { ThemeToggle } from "@/components/theme/theme-toggle";

export default function SettingsPage() {
  const version = useQuery({ queryKey: ["version"], queryFn: api.settings.version });
  const paths = useQuery({ queryKey: ["config-paths"], queryFn: api.settings.paths });
  const settings = useQuery({ queryKey: ["settings"], queryFn: api.settings.all });

  const doctor = useMutation({ mutationFn: () => api.settings.doctor() });

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-end justify-between gap-6">
        <div className="space-y-1">
          <h1 className="page-title">Settings</h1>
          <p className="page-subtitle">
            Configuration, directories, and diagnostics
          </p>
        </div>
        <Button className="rounded-xl" onClick={() => doctor.mutate()} disabled={doctor.isPending}>
          Run system doctor
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-[0.9375rem] font-semibold">Appearance</CardTitle>
        </CardHeader>
        <CardContent className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground">Theme</p>
          <ThemeToggle showLabel />
        </CardContent>
      </Card>

      {version.data && (
        <Card>
          <CardContent className="flex items-center gap-4 pt-6">
            <div>
              <p className="text-sm text-muted-foreground">Version</p>
              <p className="text-lg font-semibold">
                {version.data.name} {version.data.version}
              </p>
            </div>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Directories</CardTitle>
        </CardHeader>
        <CardContent>
          {paths.isLoading ? (
            <Skeleton className="h-32" />
          ) : (
            <ul className="space-y-2 text-sm">
              {(paths.data ?? []).map((p) => (
                <li key={p.key} className="flex items-center justify-between gap-4">
                  <span className="font-medium">{p.key}</span>
                  <code className="truncate text-xs text-muted-foreground">{p.path}</code>
                  <Badge variant={p.exists ? "default" : "secondary"}>
                    {p.exists ? "exists" : "missing"}
                  </Badge>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Configuration (redacted)</CardTitle>
        </CardHeader>
        <CardContent>
          {settings.isLoading ? (
            <Skeleton className="h-48" />
          ) : (
            <pre className="max-h-96 overflow-auto rounded-md bg-muted p-4 text-xs">
              {JSON.stringify(settings.data, null, 2)}
            </pre>
          )}
        </CardContent>
      </Card>

      {doctor.data != null ? (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Doctor report</CardTitle>
          </CardHeader>
          <CardContent>
            <pre className="max-h-96 overflow-auto text-xs">
              {JSON.stringify(doctor.data, null, 2)}
            </pre>
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}
