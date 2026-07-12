"use client";

import { motion } from "framer-motion";
import { cn } from "@/lib/utils";
import { useNarration } from "@/hooks/use-narration";
import { AudioControl } from "@/components/audio/audio-control";
import { Transcript } from "@/components/audio/transcript";
import { audioSrc } from "@/lib/audio";

interface NarratedSectionProps {
  id: string;
  number: string;
  title: string;
  subtitle?: string;
  /** Narration lines, also shown as the live transcript. */
  lines: string[];
  /** Custom content rendered beneath the transcript (cards, grids). */
  children?: React.ReactNode;
  className?: string;
}

/**
 * A full chapter: understated audio header, then a live transcript,
 * then any custom body. One component powers every narrated chapter.
 */
export function NarratedSection({
  id,
  number,
  title,
  subtitle,
  lines,
  children,
  className,
}: NarratedSectionProps) {
  const narration = useNarration(audioSrc(id));

  return (
    <section
      id={id}
      className={cn(
        "relative min-h-screen px-6 py-32 md:px-12 md:py-40 lg:px-24",
        className,
      )}
    >
      <div className="mx-auto max-w-3xl">
        <motion.header
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-80px" }}
          transition={{ duration: 0.7, ease: [0.25, 0.1, 0.25, 1] }}
          className="mb-16 md:mb-24"
        >
          <p className="mb-5 font-mono text-[11px] tracking-[0.35em] text-muted-foreground uppercase">
            {number}
          </p>
          <h2 className="font-serif text-5xl font-light tracking-tight text-foreground md:text-7xl">
            {title}
          </h2>
          {subtitle && (
            <p className="mt-4 text-lg font-light text-muted-foreground">
              {subtitle}
            </p>
          )}
          <div className="mt-10">
            <AudioControl
              src={audioSrc(id)}
              narration={narration}
              label={title}
            />
          </div>
        </motion.header>

        <Transcript
          lines={lines}
          progress={narration.progress}
          playing={narration.playing}
        />

        {children && <div className="mt-20">{children}</div>}
      </div>
    </section>
  );
}
