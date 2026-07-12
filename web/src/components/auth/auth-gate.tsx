"use client";

import { useEffect, useState } from "react";
import { isAuthenticated, isOnboardingComplete } from "@/lib/auth";
import { PasswordGate } from "@/components/auth/password-gate";
import { OnboardingWizard } from "@/components/auth/onboarding-wizard";
import { SeedIcon } from "@/components/brand/seed-icon";

type AuthGateProps = {
  children: React.ReactNode;
};

export function AuthGate({ children }: AuthGateProps) {
  const [ready, setReady] = useState(false);
  const [authed, setAuthed] = useState(false);
  const [onboarded, setOnboarded] = useState(false);

  useEffect(() => {
    const a = isAuthenticated();
    setAuthed(a);
    setOnboarded(a ? isOnboardingComplete() : false);
    setReady(true);
  }, []);

  if (!ready) {
    return (
      <div className="brand-gradient flex min-h-screen items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/12">
            <SeedIcon className="h-7 w-7 animate-pulse text-primary" />
          </div>
          <p className="text-sm text-muted-foreground lowercase">sedr</p>
        </div>
      </div>
    );
  }

  if (!authed) {
    return (
      <PasswordGate
        onSuccess={() => {
          setAuthed(true);
          setOnboarded(isOnboardingComplete());
        }}
      />
    );
  }

  if (!onboarded) {
    return <OnboardingWizard onComplete={() => setOnboarded(true)} />;
  }

  return <>{children}</>;
}
