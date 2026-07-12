"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { welcomeNarration } from "@/content/welcome";

interface WelcomeExperienceProps {
  onComplete: () => void;
}

export function WelcomeExperience({ onComplete }: WelcomeExperienceProps) {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isExiting, setIsExiting] = useState(false);
  const [showText, setShowText] = useState(false);

  useEffect(() => {
    const showTimer = setTimeout(() => setShowText(true), 800);
    return () => clearTimeout(showTimer);
  }, []);

  useEffect(() => {
    if (!showText) return;

    if (currentIndex >= welcomeNarration.length) {
      const exitTimer = setTimeout(() => {
        setIsExiting(true);
        setTimeout(onComplete, 1500);
      }, 2000);
      return () => clearTimeout(exitTimer);
    }

    const timer = setTimeout(() => {
      setCurrentIndex((prev) => prev + 1);
    }, welcomeNarration[currentIndex].duration);

    return () => clearTimeout(timer);
  }, [currentIndex, showText, onComplete]);

  const currentText =
    currentIndex < welcomeNarration.length
      ? welcomeNarration[currentIndex].text
      : "";

  return (
    <AnimatePresence>
      {!isExiting ? (
        <motion.div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 1.5, ease: [0.25, 0.1, 0.25, 1] }}
        >
          <div className="absolute inset-0 bg-gradient-to-b from-transparent via-transparent to-black/20" />

          <AnimatePresence mode="wait">
            {showText && currentText && (
              <motion.p
                key={currentIndex}
                className="max-w-lg px-8 text-center font-serif text-xl leading-relaxed font-light text-white/80 md:text-2xl md:leading-relaxed"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 1, ease: [0.25, 0.1, 0.25, 1] }}
              >
                {currentText}
              </motion.p>
            )}
          </AnimatePresence>
        </motion.div>
      ) : (
        <motion.div
          className="fixed inset-0 z-50 bg-black"
          initial={{ opacity: 1 }}
          animate={{ opacity: 0 }}
          transition={{ duration: 1.5 }}
        />
      )}
    </AnimatePresence>
  );
}
