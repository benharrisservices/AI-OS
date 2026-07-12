"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Check, Copy, Eye, EyeOff } from "lucide-react";
import type { CredentialItem } from "@/content/keys";
import { cn } from "@/lib/utils";

interface CredentialCardProps {
  credential: CredentialItem;
  index: number;
}

export function CredentialCard({ credential, index }: CredentialCardProps) {
  const [revealed, setRevealed] = useState(false);
  const [copied, setCopied] = useState(false);

  const hidden = credential.secret && !revealed;
  const displayValue = hidden ? "••••••••" : credential.value;

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(credential.value);
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    } catch {
      // Clipboard unavailable
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 14 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-40px" }}
      transition={{ duration: 0.5, delay: (index % 4) * 0.06 }}
      className="group flex items-baseline justify-between gap-6 border-b border-foreground/[0.06] py-5"
    >
      <div className="min-w-0 flex-1">
        <p className="mb-1.5 text-[11px] tracking-[0.15em] text-muted-foreground uppercase">
          {credential.label}
        </p>
        <p
          className={cn(
            "truncate font-mono text-sm text-foreground/85 transition-colors",
            hidden && "tracking-widest text-foreground/40",
          )}
        >
          {displayValue}
        </p>
      </div>

      <div className="flex shrink-0 items-center gap-1 opacity-60 transition-opacity group-hover:opacity-100">
        {credential.secret && (
          <button
            onClick={() => setRevealed(!revealed)}
            className="flex h-8 w-8 items-center justify-center rounded-full text-muted-foreground transition-colors hover:text-foreground"
            aria-label={revealed ? "Hide password" : "Reveal password"}
          >
            {revealed ? (
              <EyeOff className="h-3.5 w-3.5" />
            ) : (
              <Eye className="h-3.5 w-3.5" />
            )}
          </button>
        )}
        <button
          onClick={handleCopy}
          className="flex h-8 w-8 items-center justify-center rounded-full text-muted-foreground transition-colors hover:text-foreground"
          aria-label={copied ? "Copied" : `Copy ${credential.label}`}
        >
          <AnimatePresence mode="wait" initial={false}>
            {copied ? (
              <motion.span
                key="check"
                initial={{ scale: 0, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0, opacity: 0 }}
                transition={{ duration: 0.2 }}
              >
                <Check className="h-3.5 w-3.5 text-emerald-500/80" />
              </motion.span>
            ) : (
              <motion.span
                key="copy"
                initial={{ scale: 0, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0, opacity: 0 }}
                transition={{ duration: 0.2 }}
              >
                <Copy className="h-3.5 w-3.5" />
              </motion.span>
            )}
          </AnimatePresence>
        </button>
      </div>
    </motion.div>
  );
}
