"use client";

import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError, type UploadProgress } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";

export default function ImportsPage() {
  const qc = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [presetId, setPresetId] = useState("");
  const [tags, setTags] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [uploadResult, setUploadResult] = useState<UploadProgress | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const presets = useQuery({ queryKey: ["import-presets"], queryFn: api.imports.presets });

  // Prefer an existing general folder preset from the registry — never invent one.
  useEffect(() => {
    if (presetId || !presets.data?.length) return;
    const preferred =
      presets.data.find((p) => p.id === "markdown-notes") ??
      presets.data.find((p) => p.source_type === "folder") ??
      presets.data[0];
    setPresetId(preferred.id);
  }, [presets.data, presetId]);

  const upload = useMutation({
    mutationFn: () => api.imports.upload(files, presetId, tags),
    onSuccess: (data) => {
      setUploadResult(data);
      setUploadError(null);
      setFiles([]);
      if (fileInputRef.current) fileInputRef.current.value = "";
      qc.invalidateQueries({ queryKey: ["dashboard"] });
      qc.invalidateQueries({ queryKey: ["knowledge-documents"] });
    },
    onError: (err: unknown) => {
      setUploadResult(null);
      if (err instanceof ApiError) {
        const body = err.body;
        if (body && typeof body === "object" && "detail" in body) {
          const detail = (body as { detail: unknown }).detail;
          setUploadError(
            typeof detail === "string" ? detail : JSON.stringify(detail),
          );
          return;
        }
        setUploadError(err.message);
        return;
      }
      setUploadError(err instanceof Error ? err.message : String(err));
    },
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="page-title">Imports</h1>
        <p className="page-subtitle">
          Upload documents into the knowledge base
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Upload documents</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="preset">Preset</Label>
            <select
              id="preset"
              className="flex h-10 w-full rounded-xl border border-input bg-transparent px-3.5 text-[1rem] font-medium"
              value={presetId}
              onChange={(e) => setPresetId(e.target.value)}
            >
              {(presets.data ?? []).map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name} ({p.id})
                </option>
              ))}
            </select>
            {presets.isLoading && <Skeleton className="h-8 w-full" />}
          </div>

          <div className="space-y-2">
            <Label htmlFor="files">Files</Label>
            <Input
              ref={fileInputRef}
              id="files"
              type="file"
              multiple
              accept=".md,.markdown,.txt,.pdf,.docx,.html,.htm"
              onChange={(e) => setFiles(Array.from(e.target.files ?? []))}
            />
            {files.length > 0 && (
              <p className="text-sm text-muted-foreground">
                {files.length} file{files.length === 1 ? "" : "s"} selected
                {" · "}
                {(files.reduce((n, f) => n + f.size, 0) / 1024).toFixed(1)} KB
              </p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="tags">Tags (optional, comma-separated)</Label>
            <Input
              id="tags"
              value={tags}
              onChange={(e) => setTags(e.target.value)}
              placeholder="personal, notes"
            />
          </div>

          <Button
            onClick={() => upload.mutate()}
            disabled={!presetId || files.length === 0 || upload.isPending}
          >
            {upload.isPending ? "Uploading…" : "Upload & index"}
          </Button>

          {upload.isPending && (
            <p className="text-sm text-muted-foreground">
              Uploading and indexing — this may take a moment…
            </p>
          )}

          {uploadError && (
            <div
              className="rounded-xl border border-destructive/40 bg-destructive/10 p-4 text-sm text-destructive"
              role="alert"
            >
              {uploadError}
            </div>
          )}

          {uploadResult && (
            <div className="space-y-3 rounded-xl border border-border p-4 text-sm">
              <div className="flex flex-wrap gap-2">
                <Badge variant="default">
                  Ingested {uploadResult.ingested}
                </Badge>
                <Badge variant="outline">Skipped {uploadResult.skipped}</Badge>
                <Badge variant="outline">Failed {uploadResult.failed}</Badge>
                {uploadResult.duplicate_files != null &&
                  uploadResult.duplicate_files > 0 && (
                    <Badge variant="secondary">
                      Duplicates {uploadResult.duplicate_files}
                    </Badge>
                  )}
              </div>
              <p>
                Knowledge base:{" "}
                <strong>{uploadResult.document_count ?? "—"}</strong> documents
                {" · "}
                <strong>{uploadResult.chunk_count ?? "—"}</strong> chunks
              </p>
              {uploadResult.rejected && uploadResult.rejected.length > 0 && (
                <ul className="text-destructive">
                  {uploadResult.rejected.map((r, i) => (
                    <li key={i}>{r}</li>
                  ))}
                </ul>
              )}
              {uploadResult.errors.length > 0 && (
                <ul className="text-destructive">
                  {uploadResult.errors.map((e, i) => (
                    <li key={i}>{e}</li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      <div className="grid gap-4 md:grid-cols-2">
        {(presets.data ?? []).map((p) => (
          <Card
            key={p.id}
            className={`cursor-pointer transition-colors ${presetId === p.id ? "ring-2 ring-primary" : ""}`}
            onClick={() => setPresetId(p.id)}
          >
            <CardHeader>
              <CardTitle className="text-base">{p.name}</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">{p.description}</p>
              <p className="mt-2 text-xs text-muted-foreground">{p.id}</p>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
