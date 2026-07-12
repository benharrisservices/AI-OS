export const chapters = [
  { id: "welcome", title: "Welcome", number: "00" },
  { id: "identity", title: "Identity", number: "01" },
  { id: "keys", title: "The Keys", number: "02" },
  { id: "principles", title: "The Principles", number: "03" },
  { id: "freedom", title: "Freedom", number: "04" },
  { id: "learning", title: "Learning", number: "05" },
  { id: "health", title: "Health", number: "06" },
  { id: "money", title: "Money", number: "07" },
  { id: "business", title: "Business", number: "08" },
  { id: "technology", title: "Technology", number: "09" },
  { id: "ai", title: "Artificial Intelligence", number: "10" },
  { id: "leverage", title: "Leverage", number: "11" },
  { id: "books", title: "Books", number: "12" },
  { id: "projects", title: "Projects", number: "13" },
  { id: "resources", title: "Useful Resources", number: "14" },
  { id: "letter", title: "Final Letter", number: "15" },
] as const;

export type ChapterId = (typeof chapters)[number]["id"];
