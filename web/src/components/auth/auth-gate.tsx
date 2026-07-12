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
      <div className="flex min-h-screen items-center justify-center bg-background">
        <div className="flex flex-col items-center gap-5">
          <SeedIcon className="h-8 w-8 animate-pulse text-primary" />
          <p className="text-sm font-medium tracking-wide text-muted-foreground lowercase">
            sedr
          </p>
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
