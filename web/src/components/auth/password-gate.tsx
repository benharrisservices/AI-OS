"use client";

import { useState } from "react";
import { DEMO_PASSWORD, login } from "@/lib/auth";
import { SeedIcon } from "@/components/brand/seed-icon";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

type PasswordGateProps = {
  onSuccess: () => void;
};

export function PasswordGate({ onSuccess }: PasswordGateProps) {
  const [password, setPassword] = useState("");
  const [error, setError] = useState(false);
  const [loading, setLoading] = useState(false);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(false);
    setTimeout(() => {
      if (password === DEMO_PASSWORD) {
        login();
        onSuccess();
      } else {
        setError(true);
        setLoading(false);
      }
    }, 400);
  }

  return (
    <div className="brand-gradient flex min-h-screen items-center justify-center px-4">
      <div className="w-full max-w-sm space-y-8 text-center">
        <div className="flex flex-col items-center gap-4">
          <div className="flex h-16 w-16 items-center justify-center rounded-2xl brand-gradient-strong">
            <SeedIcon className="h-8 w-8 text-primary-foreground" />
          </div>
          <div>
            <h1 className="text-2xl font-semibold tracking-tight lowercase">sedr</h1>
            <p className="mt-1 text-sm text-muted-foreground">
              Personal Intelligence Platform
            </p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4 text-left">
          <div className="space-y-2">
            <label htmlFor="password" className="text-sm font-medium">
              Access password
            </label>
            <Input
              id="password"
              type="password"
              placeholder="Enter password"
              value={password}
              onChange={(e) => {
                setPassword(e.target.value);
                setError(false);
              }}
              autoFocus
              autoComplete="current-password"
              className="h-11 rounded-xl"
            />
            {error && (
              <p className="text-sm text-destructive" role="alert">
                Incorrect password. Please try again.
              </p>
            )}
          </div>
          <Button
            type="submit"
            className="h-11 w-full rounded-xl"
            disabled={loading || !password}
          >
            {loading ? "Verifying…" : "Enter sedr"}
          </Button>
        </form>

        <p className="text-xs text-muted-foreground">
          Private demo · sedr.ca
        </p>
      </div>
    </div>
  );
}
