export const AUTH_SESSION_KEY = "sedr_auth_session";
export const AUTH_PERSIST_KEY = "sedr_auth";
export const AUTH_EXPIRY_KEY = "sedr_auth_expiry";
export const ONBOARDING_KEY = "sedr_onboarding_complete";
export const DEMO_PASSWORD = "kijio";

const REMEMBER_MS = 24 * 60 * 60 * 1000;

function clearAuth(): void {
  sessionStorage.removeItem(AUTH_SESSION_KEY);
  localStorage.removeItem(AUTH_PERSIST_KEY);
  localStorage.removeItem(AUTH_EXPIRY_KEY);
}

export function isAuthenticated(): boolean {
  if (typeof window === "undefined") return false;

  if (sessionStorage.getItem(AUTH_SESSION_KEY) === "true") return true;

  if (localStorage.getItem(AUTH_PERSIST_KEY) !== "true") return false;

  const expiry = localStorage.getItem(AUTH_EXPIRY_KEY);
  if (!expiry) {
    clearAuth();
    return false;
  }

  if (Date.now() > Number(expiry)) {
    clearAuth();
    return false;
  }

  return true;
}

export function login(remember = false): void {
  if (remember) {
    localStorage.setItem(AUTH_PERSIST_KEY, "true");
    localStorage.setItem(AUTH_EXPIRY_KEY, String(Date.now() + REMEMBER_MS));
    sessionStorage.removeItem(AUTH_SESSION_KEY);
  } else {
    sessionStorage.setItem(AUTH_SESSION_KEY, "true");
    localStorage.removeItem(AUTH_PERSIST_KEY);
    localStorage.removeItem(AUTH_EXPIRY_KEY);
  }
}

export function logout(): void {
  clearAuth();
  window.location.href = "/";
}

export function isOnboardingComplete(): boolean {
  if (typeof window === "undefined") return true;
  return localStorage.getItem(ONBOARDING_KEY) === "true";
}

export function completeOnboarding(): void {
  localStorage.setItem(ONBOARDING_KEY, "true");
}
