"use client";

import Link from "next/link";
import { RefreshCw, Stethoscope } from "lucide-react";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

type BackendUnavailableProps = {
  onRetry: () => void;
  isRetrying?: boolean;
};

export function BackendUnavailable({
  onRetry,
  isRetrying = false,
}: BackendUnavailableProps) {
  return (
    <Card className="mx-auto max-w-xl border-border/70 shadow-soft">
      <CardHeader className="space-y-2 text-center">
        <CardTitle className="text-[1.375rem] font-bold tracking-[-0.02em]">
          Backend unavailable
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-6 text-center">
        <p className="text-[1.0625rem] leading-relaxed text-muted-foreground">
          sedr is running, but its intelligence engine is currently offline.
        </p>
        <div className="flex flex-wrap items-center justify-center gap-3">
          <Button
            onClick={onRetry}
            disabled={isRetrying}
            className="min-w-[7rem]"
          >
            <RefreshCw
              className={`mr-2 h-4 w-4 ${isRetrying ? "animate-spin" : ""}`}
              aria-hidden
            />
            {isRetrying ? "Retrying…" : "Retry"}
          </Button>
          <Link
            href="/providers"
            className={cn(buttonVariants({ variant: "outline", size: "default" }))}
          >
            <Stethoscope className="mr-2 h-4 w-4" aria-hidden />
            View diagnostics
          </Link>
        </div>
      </CardContent>
    </Card>
  );
}
