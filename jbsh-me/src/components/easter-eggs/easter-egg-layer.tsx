"use client";

import { useEffect, useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";

const STARS = Array.from({ length: 24 }, (_, i) => ({
  id: i,
  x: (i * 17 + 13) % 100,
  y: (i * 23 + 7) % 100,
  size: (i % 3) * 0.5 + 0.5,
  delay: (i % 5) * 0.4,
}));

export function EasterEggLayer() {
  const [logoMessage, setLogoMessage] = useState(false);
  const [constellation, setConstellation] = useState(false);
  const [jQuote, setJQuote] = useState(false);
  const [shiftHeld, setShiftHeld] = useState(false);
  const [shiftTimer, setShiftTimer] = useState<NodeJS.Timeout | null>(null);

  const handleLogoDoubleClick = useCallback(() => {
    setLogoMessage(true);
    setTimeout(() => setLogoMessage(false), 3000);
  }, []);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Shift" && !shiftHeld) {
        setShiftHeld(true);
        const timer = setTimeout(() => setConstellation(true), 3000);
        setShiftTimer(timer);
      }

      if (e.key === "j" || e.key === "J") {
        setJQuote(true);
        setTimeout(() => setJQuote(false), 5000);
      }
    };

    const handleKeyUp = (e: KeyboardEvent) => {
      if (e.key === "Shift") {
        setShiftHeld(false);
        if (shiftTimer) clearTimeout(shiftTimer);
        setConstellation(false);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    window.addEventListener("keyup", handleKeyUp);

    return () => {
      window.removeEventListener("keydown", handleKeyDown);
      window.removeEventListener("keyup", handleKeyUp);
      if (shiftTimer) clearTimeout(shiftTimer);
    };
  }, [shiftHeld, shiftTimer]);

  useEffect(() => {
    (window as unknown as Record<string, unknown>).__jbshLogoDblClick =
      handleLogoDoubleClick;
    return () => {
      delete (window as unknown as Record<string, unknown>).__jbshLogoDblClick;
    };
  }, [handleLogoDoubleClick]);

  return (
    <>
      <AnimatePresence>
        {logoMessage && (
          <motion.p
            className="fixed top-1/2 left-1/2 z-[100] -translate-x-1/2 -translate-y-1/2 font-serif text-sm text-foreground/40"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.8 }}
          >
            Keep going.
          </motion.p>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {constellation && (
          <motion.div
            className="pointer-events-none fixed inset-0 z-[90]"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 2 }}
          >
            {STARS.map((star) => (
              <motion.div
                key={star.id}
                className="absolute rounded-full bg-foreground/20"
                style={{
                  left: `${star.x}%`,
                  top: `${star.y}%`,
                  width: star.size,
                  height: star.size,
                }}
                initial={{ opacity: 0, scale: 0 }}
                animate={{ opacity: [0, 0.6, 0.3], scale: 1 }}
                transition={{
                  duration: 3,
                  delay: star.delay,
                  ease: "easeOut",
                }}
              />
            ))}
          </motion.div>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {jQuote && (
          <motion.div
            className="pointer-events-none fixed inset-0 z-[90] flex items-center justify-center"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 1 }}
          >
            <motion.div
              className="absolute inset-0 bg-foreground/[0.02]"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            />
            <motion.p
              className="max-w-md px-8 text-center font-serif text-lg text-foreground/30 italic"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              transition={{ delay: 0.3 }}
            >
              &ldquo;The future is already here. It&apos;s just not evenly
              distributed.&rdquo;
              <span className="mt-2 block text-sm not-italic text-foreground/20">
                William Gibson
              </span>
            </motion.p>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
