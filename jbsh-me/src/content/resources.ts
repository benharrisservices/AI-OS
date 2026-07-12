export interface ResourceCategory {
  category: string;
  items: { name: string; url: string; description: string }[];
}

export const resourcesIntro: string[] = [
  "Starting points.",
  "Not prescriptions.",
  "Follow what interests you. Ignore the rest.",
];

export const resources: ResourceCategory[] = [
  {
    category: "Reading",
    items: [
      { name: "Paul Graham", url: "https://paulgraham.com/articles.html", description: "The essays that started a genre." },
      { name: "Stratechery", url: "https://stratechery.com", description: "Technology strategy, made clear." },
      { name: "Hacker News", url: "https://news.ycombinator.com", description: "Where the technical world argues." },
      { name: "Dense Discovery", url: "https://densediscovery.com", description: "A quiet weekly for design and thought." },
    ],
  },
  {
    category: "Watching",
    items: [
      { name: "NetworkChuck", url: "https://youtube.com/@NetworkChuck", description: "Networking, made fun." },
      { name: "Fireship", url: "https://youtube.com/@Fireship", description: "Clarity in a hundred seconds." },
      { name: "Theo", url: "https://youtube.com/@t3dotgg", description: "Honest opinions on building software." },
      { name: "Acquired", url: "https://acquired.fm", description: "How the best companies were built." },
    ],
  },
  {
    category: "Tools",
    items: [
      { name: "Vercel", url: "https://vercel.com", description: "Deploy in seconds. Your hosting home." },
      { name: "GitHub", url: "https://github.com", description: "Where your work becomes visible." },
      { name: "Obsidian", url: "https://obsidian.md", description: "A second brain, local and yours." },
      { name: "Cursor", url: "https://cursor.com", description: "Build faster than you thought you could." },
    ],
  },
];
