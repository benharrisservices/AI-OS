"use client";

import { useState, useEffect, useCallback } from "react";
import { PasswordGate } from "@/components/gate/password-gate";
import { WelcomeExperience } from "@/components/welcome/welcome-experience";
import { MainSite } from "@/components/site/main-site";
import { STORAGE_KEYS } from "@/lib/constants";
import { getStorageItem, setStorageItem } from "@/lib/storage";

type AppState = "loading" | "gate" | "welcome" | "site";

export default function Home() {
  const [appState, setAppState] = useState<AppState>("loading");

  useEffect(() => {
    queueMicrotask(() => {
      const authenticated = getStorageItem(STORAGE_KEYS.authenticated);
      const welcomeSeen = getStorageItem(STORAGE_KEYS.welcomeSeen);

      if (!authenticated) {
        setAppState("gate");
      } else if (!welcomeSeen) {
        setAppState("welcome");
      } else {
        setAppState("site");
      }
    });
  }, []);

  const handleGateSuccess = useCallback(() => {
    setStorageItem(STORAGE_KEYS.authenticated, "true");
    const welcomeSeen = getStorageItem(STORAGE_KEYS.welcomeSeen);
    setAppState(welcomeSeen ? "site" : "welcome");
  }, []);

  const handleWelcomeComplete = useCallback(() => {
    setStorageItem(STORAGE_KEYS.welcomeSeen, "true");
    setAppState("site");
  }, []);

  if (appState === "loading") {
    return <div className="fixed inset-0 bg-black" />;
  }

  return (
    <>
      {appState === "gate" && <PasswordGate onSuccess={handleGateSuccess} />}
      {appState === "welcome" && (
        <WelcomeExperience onComplete={handleWelcomeComplete} />
      )}
      {appState === "site" && <MainSite />}
    </>
  );
}
