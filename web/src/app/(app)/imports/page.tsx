"use client";

import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";

export default function ImportsPage() {
  const [presetId, setPresetId] = useState("");
  const [sourcePath, setSourcePath] = useState("");
  const [validation, setValidation] = useState<Awaited<
    ReturnType<typeof api.imports.validate>
  > | null>(null);

  const presets = useQuery({ queryKey: ["import-presets"], queryFn: api.imports.presets });

  const validate = useMutation({
    mutationFn: () => api.imports.validate(presetId, sourcePath),
    onSuccess: setValidation,
  });

  const runImport = useMutation({
    mutationFn: () => api.imports.run(presetId, sourcePath),
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Imports</h1>
        <p className="text-sm text-muted-foreground">Validate and import knowledge sources</p>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        {(presets.data ?? []).map((p) => (
          <Card
            key={p.id}
            className={`cursor-pointer transition-colors ${presetId === p.id ? "ring-2 ring-primary" : ""}`}
            onClick={() => {
              setPresetId(p.id);
              setSourcePath(p.suggested_path);
            }}
          >
            <CardHeader>
              <CardTitle className="text-base">{p.name}</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">{p.description}</p>
              <p className="mt-2 text-xs text-muted-foreground">{p.suggested_path}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Import configuration</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="preset">Preset ID</Label>
            <Input
              id="preset"
              value={presetId}
              onChange={(e) => setPresetId(e.target.value)}
              placeholder="ai-os-repo"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="path">Source path</Label>
            <Input
              id="path"
              value={sourcePath}
              onChange={(e) => setSourcePath(e.target.value)}
              placeholder="./docs"
            />
          </div>
          <div className="flex gap-2">
            <Button
              onClick={() => validate.mutate()}
              disabled={!presetId || !sourcePath || validate.isPending}
            >
              Validate
            </Button>
            <Button
              variant="default"
              onClick={() => runImport.mutate()}
              disabled={!validation?.ready || runImport.isPending}
            >
              Import
            </Button>
          </div>
          {validate.isPending && <Skeleton className="h-20" />}
          {validation && (
            <div className="rounded-md border border-border p-4 text-sm">
              <div className="flex flex-wrap gap-2">
                <Badge variant={validation.ready ? "default" : "secondary"}>
                  {validation.ready ? "Ready" : "Not ready"}
                </Badge>
                <Badge variant="outline">{validation.new_files} new files</Badge>
                <Badge variant="outline">~{validation.estimated_minutes} min</Badge>
              </div>
              {validation.errors.length > 0 && (
                <ul className="mt-2 text-destructive">
                  {validation.errors.map((e, i) => (
                    <li key={i}>{e}</li>
                  ))}
                </ul>
              )}
            </div>
          )}
          {runImport.data && (
            <pre className="rounded-md bg-muted p-3 text-xs">
              {JSON.stringify(runImport.data, null, 2)}
            </pre>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
