export interface Book {
  title: string;
  author: string;
  description: string;
}

export const booksIntro: string[] = [
  "Read things that change you.",
  "These did that for me.",
  "The ones that land will stay for years.",
];

export const books: Book[] = [
  {
    title: "Atomic Habits",
    author: "James Clear",
    description: "You fall to the level of your systems. Build better ones.",
  },
  {
    title: "Poor Charlie's Almanack",
    author: "Charlie Munger",
    description: "Think across every discipline. See what others miss.",
  },
  {
    title: "The Almanack of Naval Ravikant",
    author: "Eric Jorgenson",
    description: "Wealth and happiness, explained with unusual clarity.",
  },
  {
    title: "The Psychology of Money",
    author: "Morgan Housel",
    description: "Money is rarely about the maths. It is about behaviour.",
  },
  {
    title: "Zero to One",
    author: "Peter Thiel",
    description: "The best companies make something new, not something more.",
  },
  {
    title: "The Sovereign Individual",
    author: "Davidson & Rees-Mogg",
    description: "Written in 1997. Somehow about the world you live in now.",
  },
  {
    title: "Deep Work",
    author: "Cal Newport",
    description: "Focus is becoming the rarest skill. Protect yours.",
  },
  {
    title: "Meditations",
    author: "Marcus Aurelius",
    description: "Two thousand years old. Still steadier than the news.",
  },
  {
    title: "The War of Art",
    author: "Steven Pressfield",
    description: "Names the thing that stops you. Then hands you a weapon.",
  },
  {
    title: "Never Split the Difference",
    author: "Chris Voss",
    description: "Negotiation as listening, not combat.",
  },
];
