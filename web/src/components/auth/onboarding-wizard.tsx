"use client";

import { useState } from "react";
import {
  Home,
  Layers,
  Plug,
  Workflow,
} from "lucide-react";
import { completeOnboarding } from "@/lib/auth";
import { SeedIcon } from "@/components/brand/seed-icon";
import { Button } from "@/components/ui/button";

type OnboardingWizardProps = {
  onComplete: () => void;
};

const SCREENS = [
  {
    icon: SeedIcon,
    title: "Welcome to sedr.",
    body: "Your personal intelligence platform — a calm, unified place to think, decide, and act with AI.",
  },
  {
    icon: Layers,
    title: "Knowledge",
    body: "Documents, notes, PDFs, and projects become searchable memory. Import once, retrieve forever.",
  },
  {
    icon: Plug,
    title: "Providers",
    body: "Connect AI models, GitHub, email, and calendars. Local models first, cloud when you need them.",
  },
  {
    icon: Workflow,
    title: "Workflows",
    body: "Morning briefings, daily reviews, research runs, and automations — scheduled or on demand.",
  },
  {
    icon: Home,
    title: "Dashboard",
    body: "Knowledge, Memory, Decisions, Agents, Workflows, Automations, Imports, Providers, Models, and Settings — all in one place.",
  },
  {
    icon: SeedIcon,
    title: "You're ready.",
    body: "Launch the dashboard and explore your personal intelligence platform.",
    isFinal: true,
  },
] as const;

export function OnboardingWizard({ onComplete }: OnboardingWizardProps) {
  const [step, setStep] = useState(0);
  const screen = SCREENS[step];
  const Icon = screen.icon;
  const isFinal = "isFinal" in screen && screen.isFinal;

  function finish() {
    completeOnboarding();
    onComplete();
  }

  return (
    <div className="brand-gradient fixed inset-0 z-50 flex items-center justify-center px-4">
      <div className="w-full max-w-lg space-y-8 text-center">
        <div className="flex justify-center gap-2">
          {SCREENS.map((_, i) => (
            <div
              key={i}
              className={`h-1.5 rounded-full transition-all ${
                i === step
                  ? "w-8 bg-primary"
                  : i < step
                    ? "w-4 bg-primary/40"
                    : "w-4 bg-muted"
              }`}
            />
          ))}
        </div>

        <div className="space-y-6 rounded-3xl border border-border bg-card p-10 ring-1 ring-foreground/8">
          <div className="flex justify-center">
            <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/12">
              <Icon className="h-7 w-7 text-primary" />
            </div>
          </div>
          <div className="space-y-3">
            <h2 className="text-xl font-semibold tracking-tight">{screen.title}</h2>
            <p className="text-sm leading-relaxed text-muted-foreground">{screen.body}</p>
          </div>
        </div>

        <div className="flex items-center justify-between gap-4">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setStep((s) => Math.max(0, s - 1))}
            disabled={step === 0}
            className="rounded-xl"
          >
            Back
          </Button>
          {isFinal ? (
            <Button onClick={finish} className="rounded-xl px-8">
              Launch Dashboard
            </Button>
          ) : (
            <Button
              onClick={() => setStep((s) => s + 1)}
              className="rounded-xl px-8"
            >
              Continue
            </Button>
          )}
        </div>

        {!isFinal && (
          <button
            type="button"
            onClick={finish}
            className="text-xs text-muted-foreground hover:text-foreground"
          >
            Skip tour
          </button>
        )}
      </div>
    </div>
  );
}
