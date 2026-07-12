"use client";

import { useMemo, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useNarration } from "@/hooks/use-narration";
import { AudioControl } from "@/components/audio/audio-control";
import { audioSrc } from "@/lib/audio";
import { finalLetter } from "@/content/letter";
import { cn } from "@/lib/utils";

export function FinalLetterSection() {
  const narration = useNarration(audioSrc("letter"));
  const [showClosing, setShowClosing] = useState(false);
  const [triggered, setTriggered] = useState(false);

  const lines = finalLetter.lines;

  const activeIndex = useMemo(() => {
    if (narration.progress <= 0) return -1;
    const idx = Math.floor(narration.progress * lines.length);
    return Math.min(idx, lines.length - 1);
  }, [narration.progress, lines.length]);

  const revealClosing = () => {
    if (triggered) return;
    setTriggered(true);
    setTimeout(() => setShowClosing(true), 2600);
  };

  return (
    <>
      <section
        id="letter"
        className="relative min-h-screen px-6 py-32 md:px-12 md:py-40 lg:px-24"
      >
        <div className="mx-auto max-w-2xl">
          <motion.header
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-80px" }}
            transition={{ duration: 0.7 }}
            className="mb-16"
          >
            <p className="mb-5 font-mono text-[11px] tracking-[0.35em] text-muted-foreground uppercase">
              15
            </p>
            <h2 className="font-serif text-5xl font-light tracking-tight text-foreground md:text-7xl">
              {finalLetter.title}
            </h2>
            <div className="mt-10">
              <AudioControl
                src={audioSrc("letter")}
                narration={narration}
                label="the final letter"
              />
            </div>
          </motion.header>

          <div className="space-y-6">
            {lines.map((line, i) => {
              const isActive = i === activeIndex;
              const isPast = activeIndex >= 0 && i < activeIndex;
              const isLast = i === lines.length - 1;
              return (
                <motion.p
                  key={i}
                  initial={{ opacity: 0, y: 10 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true, margin: "-30px" }}
                  transition={{ duration: 0.5, delay: Math.min(i, 6) * 0.05 }}
                  onAnimationComplete={isLast ? revealClosing : undefined}
                  className={cn(
                    "font-serif text-xl leading-relaxed font-light tracking-tight transition-colors duration-700 md:text-2xl md:leading-relaxed",
                    isActive && "text-foreground",
                    isPast && "text-foreground/40",
                    !isActive && !isPast && "text-foreground/70",
                  )}
                >
                  {line}
                </motion.p>
              );
            })}
          </div>
        </div>
      </section>

      <AnimatePresence>
        {showClosing && (
          <motion.div
            className="fixed inset-0 z-[60] flex items-center justify-center bg-black"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 2, ease: [0.25, 0.1, 0.25, 1] }}
          >
            <motion.p
              className="max-w-md px-8 text-center font-serif text-xl leading-relaxed font-light text-white/70 md:text-2xl"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 1.6, delay: 1 }}
            >
              {finalLetter.closing.split("\n").map((line, i) => (
                <span key={i}>
                  {line}
                  {i === 0 && <br />}
                </span>
              ))}
            </motion.p>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
