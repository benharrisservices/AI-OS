"use client";

import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

const BAR_COUNT = 40;

// Deterministic pseudo-random heights so the waveform is stable across renders.
const BARS = Array.from({ length: BAR_COUNT }, (_, i) => {
  const seed = Math.sin(i * 12.9898) * 43758.5453;
  const frac = seed - Math.floor(seed);
  return 0.28 + frac * 0.72;
});

interface WaveformProps {
  /** 0 to 1 playback position. */
  progress: number;
  playing: boolean;
  onSeek?: (fraction: number) => void;
  className?: string;
}

export function Waveform({ progress, playing, onSeek, className }: WaveformProps) {
  const seekFromClientX = (clientX: number, element: HTMLDivElement) => {
    if (!onSeek) return;
    const rect = element.getBoundingClientRect();
    onSeek((clientX - rect.left) / rect.width);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLDivElement>) => {
    if (!onSeek) return;
    if (e.key === "ArrowRight") {
      e.preventDefault();
      onSeek(Math.min(progress + 0.05, 1));
    } else if (e.key === "ArrowLeft") {
      e.preventDefault();
      onSeek(Math.max(progress - 0.05, 0));
    }
  };

  return (
    <div
      className={cn(
        "flex h-6 items-center gap-[2px]",
        onSeek && "cursor-pointer",
        className,
      )}
      onClick={(e) => seekFromClientX(e.clientX, e.currentTarget)}
      onKeyDown={handleKeyDown}
      role={onSeek ? "slider" : undefined}
      aria-label={onSeek ? "Seek" : undefined}
      aria-valuemin={onSeek ? 0 : undefined}
      aria-valuemax={onSeek ? 100 : undefined}
      aria-valuenow={onSeek ? Math.round(progress * 100) : undefined}
      tabIndex={onSeek ? 0 : undefined}
    >
      {BARS.map((height, i) => {
        const played = i / BAR_COUNT <= progress;
        return (
          <motion.span
            key={i}
            className={cn(
              "w-[2px] rounded-full",
              played ? "bg-foreground/70" : "bg-foreground/20",
            )}
            style={{ height: `${height * 100}%` }}
            animate={
              playing
                ? { scaleY: [1, 0.55 + height * 0.4, 1] }
                : { scaleY: 1 }
            }
            transition={
              playing
                ? {
                    duration: 1.1 + (i % 5) * 0.12,
                    repeat: Infinity,
                    ease: "easeInOut",
                    delay: (i % 7) * 0.05,
                  }
                : { duration: 0.3 }
            }
          />
        );
      })}
    </div>
  );
}
