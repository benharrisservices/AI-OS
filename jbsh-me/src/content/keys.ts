export interface CredentialItem {
  id: string;
  label: string;
  value: string;
  /** Passwords are hidden by default. Everything else is always visible. */
  secret: boolean;
}

export const keysIntro: string[] = [
  "These are yours.",
  "Set up, and waiting.",
  "A brother leaving keys under the mat.",
];

export const credentialCards: CredentialItem[] = [
  { id: "apple-id", label: "Apple ID", value: "jbsh.me@icloud.com", secret: false },
  { id: "domain", label: "Domain", value: "jbsh.me", secret: false },
  { id: "website", label: "Website", value: "https://jbsh.me", secret: false },
  { id: "spaceship-user", label: "Spaceship", value: "jbsh.me@icloud.com", secret: false },
  { id: "github", label: "GitHub", value: "github.com/jbsh-me", secret: false },
  { id: "vercel", label: "Vercel", value: "vercel.com/jbsh-me", secret: false },
  { id: "spaceship-pass", label: "Spaceship password", value: "poloko123!", secret: true },
  { id: "website-pass", label: "Website password", value: "poloko", secret: true },
];
