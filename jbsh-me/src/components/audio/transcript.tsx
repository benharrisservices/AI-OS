"use client";

import { useEffect, useMemo, useRef } from "react";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

interface TranscriptProps {
  lines: string[];
  /** 0 to 1 playback position. */
  progress: number;
  playing: boolean;
  className?: string;
}

/**
 * Elegant sentence-level highlighting. The active line brightens, past
 * lines fade, future lines stay muted. Timing is weighted by line length,
 * so it stays reasonable for any audio file dropped in later.
 */
export function Transcript({
  lines,
  progress,
  playing,
  className,
}: TranscriptProps) {
  const activeRef = useRef<HTMLParagraphElement | null>(null);

  // Cumulative weights approximate when each line is spoken.
  const boundaries = useMemo(() => {
    const weights = lines.map((l) => Math.max(l.length, 8));
    const total = weights.reduce((a, b) => a + b, 0) || 1;
    const cumulative = weights.reduce<number[]>((acc, w) => {
      const prev = acc.length ? acc[acc.length - 1] : 0;
      acc.push(prev + w);
      return acc;
    }, []);
    return cumulative.map((c) => c / total);
  }, [lines]);

  const activeIndex = useMemo(() => {
    if (progress <= 0) return -1;
    for (let i = 0; i < boundaries.length; i++) {
      if (progress <= boundaries[i]) return i;
    }
    return lines.length - 1;
  }, [progress, boundaries, lines.length]);

  useEffect(() => {
    if (!playing || activeIndex < 0) return;
    activeRef.current?.scrollIntoView({
      behavior: "smooth",
      block: "center",
    });
  }, [activeIndex, playing]);

  return (
    <div className={cn("space-y-5", className)}>
      {lines.map((line, i) => {
        const isActive = i === activeIndex;
        const isPast = activeIndex >= 0 && i < activeIndex;
        return (
          <motion.p
            key={i}
            ref={isActive ? activeRef : null}
            initial={{ opacity: 0, y: 12 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-40px" }}
            transition={{ duration: 0.5, delay: Math.min(i, 6) * 0.04 }}
            className={cn(
              "text-2xl leading-relaxed font-light tracking-tight transition-colors duration-700 md:text-3xl md:leading-[1.5]",
              isActive && "text-foreground",
              isPast && "text-foreground/35",
              !isActive && !isPast && "text-foreground/55",
            )}
          >
            {line}
          </motion.p>
        );
      })}
    </div>
  );
}
