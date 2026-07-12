"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { chapters } from "@/content/sections";

export function Navigation() {
  const [activeSection, setActiveSection] = useState("welcome");
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      setVisible(window.scrollY > 300);

      const anchor = window.innerHeight * 0.4;
      for (const ch of [...chapters].reverse()) {
        const el = document.getElementById(ch.id);
        if (el && el.getBoundingClientRect().top <= anchor) {
          setActiveSection(ch.id);
          break;
        }
      }
    };

    window.addEventListener("scroll", handleScroll, { passive: true });
    handleScroll();
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  const scrollTo = (id: string) => {
    document.getElementById(id)?.scrollIntoView({ behavior: "smooth" });
  };

  return (
    <motion.nav
      className="fixed left-8 top-1/2 z-40 hidden -translate-y-1/2 flex-col gap-4 lg:flex"
      initial={{ opacity: 0 }}
      animate={{ opacity: visible ? 1 : 0 }}
      transition={{ duration: 0.6 }}
      aria-label="Chapters"
    >
      {chapters.map((chapter) => {
        const active = activeSection === chapter.id;
        return (
          <button
            key={chapter.id}
            onClick={() => scrollTo(chapter.id)}
            className="group flex items-center gap-3"
            aria-current={active ? "true" : undefined}
            aria-label={chapter.title}
          >
            <motion.span
              className="block h-px rounded-full"
              animate={{
                width: active ? 22 : 10,
                opacity: active ? 0.9 : 0.25,
              }}
              transition={{ duration: 0.5, ease: [0.25, 0.1, 0.25, 1] }}
              style={{
                background: "currentColor",
                boxShadow: active ? "0 0 8px currentColor" : "none",
              }}
            />
            <span
              className={`text-[10px] tracking-[0.15em] uppercase transition-opacity duration-300 ${
                active
                  ? "text-foreground/60 opacity-100"
                  : "text-foreground/40 opacity-0 group-hover:opacity-100"
              }`}
            >
              {chapter.title}
            </span>
          </button>
        );
      })}
    </motion.nav>
  );
}
