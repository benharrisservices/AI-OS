"use client";

import { Pause, Play } from "lucide-react";
import { motion } from "framer-motion";
import type { NarrationState } from "@/hooks/use-narration";
import { Waveform } from "@/components/audio/waveform";

function formatTime(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds < 0) return "0:00";
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

interface AudioControlProps {
  src: string;
  narration: NarrationState;
  label: string;
}

/**
 * Understated per-chapter audio control: play/pause, elapsed time,
 * a subtle waveform. Deliberately smaller than a media player.
 */
export function AudioControl({ src, narration, label }: AudioControlProps) {
  const { audioRef, playing, toggle, seek, progress, currentTime, duration } =
    narration;

  return (
    <div className="flex items-center gap-4">
      <audio ref={audioRef} src={src} preload="metadata" />

      <motion.button
        onClick={toggle}
        whileTap={{ scale: 0.94 }}
        className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-foreground/10 text-foreground/70 transition-colors hover:border-foreground/25 hover:text-foreground"
        aria-label={playing ? `Pause ${label}` : `Play ${label}`}
      >
        {playing ? (
          <Pause className="h-3.5 w-3.5" />
        ) : (
          <Play className="h-3.5 w-3.5 translate-x-[1px]" />
        )}
      </motion.button>

      <Waveform
        progress={progress}
        playing={playing}
        onSeek={seek}
        className="w-28 md:w-36"
      />

      <span className="font-mono text-[11px] tabular-nums text-muted-foreground">
        {formatTime(currentTime)}
        <span className="text-foreground/20"> / </span>
        {formatTime(duration)}
      </span>
    </div>
  );
}
