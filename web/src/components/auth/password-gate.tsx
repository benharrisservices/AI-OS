"use client";

import { useState } from "react";
import { DEMO_PASSWORD, login } from "@/lib/auth";
import { SeedIcon } from "@/components/brand/seed-icon";
import { ThemeToggle } from "@/components/theme/theme-toggle";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

type PasswordGateProps = {
  onSuccess: () => void;
};

export function PasswordGate({ onSuccess }: PasswordGateProps) {
  const [password, setPassword] = useState("");
  const [remember, setRemember] = useState(false);
  const [error, setError] = useState(false);
  const [loading, setLoading] = useState(false);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!password) return;
    setLoading(true);
    setError(false);
    window.setTimeout(() => {
      if (password === DEMO_PASSWORD) {
        login(remember);
        onSuccess();
      } else {
        setError(true);
        setLoading(false);
      }
    }, 280);
  }

  return (
    <div className="relative flex min-h-screen flex-col items-center justify-center bg-background px-6">
      <div className="absolute right-6 top-6">
        <ThemeToggle />
      </div>

      <div className="w-full max-w-[280px] space-y-12">
        <div className="flex flex-col items-center gap-5 text-center">
          <SeedIcon className="h-9 w-9 text-primary" />
          <h1 className="text-[2rem] font-semibold tracking-[-0.03em] lowercase text-foreground">
            sedr
          </h1>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="space-y-2">
            <Input
              id="password"
              type="password"
              placeholder="Password"
              value={password}
              onChange={(e) => {
                setPassword(e.target.value);
                setError(false);
              }}
              autoFocus
              autoComplete="current-password"
              className={cn(
                "h-12 border-0 border-b border-border rounded-none bg-transparent px-0 text-center text-base shadow-none",
                "focus-visible:border-primary focus-visible:ring-0",
                error && "border-destructive",
              )}
            />
            {error && (
              <p className="text-center text-sm text-destructive" role="alert">
                Incorrect password
              </p>
            )}
          </div>

          <label className="flex cursor-pointer items-center justify-center gap-2.5 text-sm text-muted-foreground">
            <input
              type="checkbox"
              checked={remember}
              onChange={(e) => setRemember(e.target.checked)}
              className="h-4 w-4 rounded border-border accent-primary"
            />
            Remember me for 24 hours
          </label>

          <Button
            type="submit"
            className="h-11 w-full rounded-xl md:hidden"
            disabled={loading || !password}
          >
            {loading ? "…" : "Continue"}
          </Button>
        </form>
      </div>
    </div>
  );
}
