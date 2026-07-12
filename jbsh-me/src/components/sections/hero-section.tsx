"use client";

import { motion } from "framer-motion";
import { SITE } from "@/lib/constants";

export function HeroSection() {
  const handleDoubleClick = () => {
    const handler = (window as unknown as Record<string, () => void>)
      .__jbshLogoDblClick;
    handler?.();
  };

  return (
    <section
      id="welcome"
      className="relative flex min-h-screen items-center justify-center px-6"
    >
      <div className="text-center">
        <motion.h1
          onDoubleClick={handleDoubleClick}
          className="cursor-default font-serif text-7xl font-light tracking-tight text-foreground select-none md:text-9xl"
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 1.4, ease: [0.25, 0.1, 0.25, 1] }}
        >
          {SITE.title}
        </motion.h1>

        <motion.p
          className="mt-8 text-lg font-light text-foreground/55 md:text-xl"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 1.4, delay: 0.7 }}
        >
          {SITE.subtitle}
        </motion.p>

        <motion.p
          className="mt-2 text-sm font-light text-muted-foreground"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 1.4, delay: 1 }}
        >
          {SITE.tagline}
        </motion.p>

        <motion.div
          className="mt-28 flex justify-center"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 1.4, delay: 1.6 }}
        >
          <motion.div
            className="h-10 w-px bg-foreground/15"
            animate={{ scaleY: [1, 0.5, 1], opacity: [0.5, 0.2, 0.5] }}
            transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
            style={{ transformOrigin: "top" }}
          />
        </motion.div>
      </div>
    </section>
  );
}
