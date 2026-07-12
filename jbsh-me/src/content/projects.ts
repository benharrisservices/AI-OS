export interface Project {
  title: string;
  description: string;
  status: "ready" | "future";
}

export const projectsIntro: string[] = [
  "Some of these exist.",
  "Some are invitations.",
  "The only missing variable is when you start.",
];

export const projects: Project[] = [
  {
    title: "jbsh.me",
    description: "This site. Your home online. Already live. Make it yours.",
    status: "ready",
  },
  {
    title: "A blog",
    description: "Write what you learn. Start with one post. Then another.",
    status: "future",
  },
  {
    title: "A homelab",
    description: "A sandbox where mistakes are free and discoveries are yours.",
    status: "future",
  },
  {
    title: "A small product",
    description: "One problem. Solved well. Priced fairly.",
    status: "future",
  },
  {
    title: "A GitHub",
    description: "Where your code lives. Where your reputation grows.",
    status: "future",
  },
  {
    title: "A newsletter",
    description: "Twelve readers and a steady voice is how most of them began.",
    status: "future",
  },
];
