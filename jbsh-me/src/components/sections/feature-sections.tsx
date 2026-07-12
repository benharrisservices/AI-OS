"use client";

import { motion } from "framer-motion";
import { NarratedSection } from "@/components/sections/narrated-section";
import { CredentialCard } from "@/components/keys/credential-card";
import { credentialCards, keysIntro } from "@/content/keys";
import { principles, principlesIntro } from "@/content/principles";
import { books, booksIntro } from "@/content/books";
import { projects, projectsIntro } from "@/content/projects";
import { resources, resourcesIntro } from "@/content/resources";

const fadeIn = {
  initial: { opacity: 0, y: 14 },
  whileInView: { opacity: 1, y: 0 },
  viewport: { once: true, margin: "-40px" },
};

export function KeysSection() {
  return (
    <NarratedSection
      id="keys"
      number="02"
      title="The Keys"
      subtitle="Everything you need to begin."
      lines={keysIntro}
    >
      <div className="border-t border-foreground/[0.06]">
        {credentialCards.map((cred, i) => (
          <CredentialCard key={cred.id} credential={cred} index={i} />
        ))}
      </div>
    </NarratedSection>
  );
}

export function PrinciplesSection() {
  return (
    <NarratedSection
      id="principles"
      number="03"
      title="The Principles"
      subtitle="Twenty quiet truths."
      lines={principlesIntro}
    >
      <div className="space-y-10">
        {principles.map((p, i) => (
          <motion.div
            key={p.title}
            {...fadeIn}
            transition={{ duration: 0.45, delay: (i % 6) * 0.04 }}
          >
            <h3 className="font-serif text-2xl font-light text-foreground">
              {p.title}
            </h3>
            <p className="mt-1.5 text-lg font-light text-muted-foreground">
              {p.body}
            </p>
          </motion.div>
        ))}
      </div>
    </NarratedSection>
  );
}

export function BooksSection() {
  return (
    <NarratedSection
      id="books"
      number="12"
      title="Books"
      subtitle="Read things that change you."
      lines={booksIntro}
    >
      <div className="border-t border-foreground/[0.06]">
        {books.map((book, i) => (
          <motion.div
            key={book.title}
            {...fadeIn}
            transition={{ duration: 0.45, delay: (i % 5) * 0.04 }}
            className="border-b border-foreground/[0.06] py-6"
          >
            <div className="flex items-baseline justify-between gap-6">
              <h3 className="font-serif text-2xl font-light text-foreground">
                {book.title}
              </h3>
              <span className="shrink-0 text-sm text-muted-foreground">
                {book.author}
              </span>
            </div>
            <p className="mt-2 text-lg font-light text-muted-foreground">
              {book.description}
            </p>
          </motion.div>
        ))}
      </div>
    </NarratedSection>
  );
}

export function ProjectsSection() {
  return (
    <NarratedSection
      id="projects"
      number="13"
      title="Projects"
      subtitle="Waiting for your attention."
      lines={projectsIntro}
    >
      <div className="border-t border-foreground/[0.06]">
        {projects.map((project, i) => (
          <motion.div
            key={project.title}
            {...fadeIn}
            transition={{ duration: 0.45, delay: (i % 5) * 0.04 }}
            className="flex items-baseline justify-between gap-6 border-b border-foreground/[0.06] py-6"
          >
            <div>
              <h3 className="font-serif text-2xl font-light text-foreground">
                {project.title}
              </h3>
              <p className="mt-1.5 text-lg font-light text-muted-foreground">
                {project.description}
              </p>
            </div>
            <span
              className={`shrink-0 text-[11px] tracking-[0.15em] uppercase ${
                project.status === "ready"
                  ? "text-emerald-500/70"
                  : "text-muted-foreground/50"
              }`}
            >
              {project.status === "ready" ? "Live" : "Soon"}
            </span>
          </motion.div>
        ))}
      </div>
    </NarratedSection>
  );
}

export function ResourcesSection() {
  return (
    <NarratedSection
      id="resources"
      number="14"
      title="Useful Resources"
      subtitle="Curated. Tested."
      lines={resourcesIntro}
    >
      <div className="space-y-14">
        {resources.map((category) => (
          <div key={category.category}>
            <h3 className="mb-6 font-mono text-[11px] tracking-[0.3em] text-muted-foreground uppercase">
              {category.category}
            </h3>
            <div className="border-t border-foreground/[0.06]">
              {category.items.map((item, i) => (
                <motion.a
                  key={item.name}
                  href={item.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  {...fadeIn}
                  transition={{ duration: 0.4, delay: i * 0.04 }}
                  className="group flex items-baseline justify-between gap-6 border-b border-foreground/[0.06] py-4"
                >
                  <span className="text-lg font-light text-foreground transition-colors group-hover:text-foreground">
                    {item.name}
                  </span>
                  <span className="text-right text-sm font-light text-muted-foreground">
                    {item.description}
                  </span>
                </motion.a>
              ))}
            </div>
          </div>
        ))}
      </div>
    </NarratedSection>
  );
}
