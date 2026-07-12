"use client";

import { useState, FormEvent, KeyboardEvent } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { SITE_PASSWORD } from "@/lib/constants";

interface PasswordGateProps {
  onSuccess: () => void;
}

export function PasswordGate({ onSuccess }: PasswordGateProps) {
  const [password, setPassword] = useState("");
  const [error, setError] = useState(false);
  const [isExiting, setIsExiting] = useState(false);

  const handleSubmit = (e?: FormEvent) => {
    e?.preventDefault();
    if (password === SITE_PASSWORD) {
      setIsExiting(true);
      setTimeout(onSuccess, 1200);
    } else {
      setError(true);
      setTimeout(() => setError(false), 2000);
    }
  };

  const handleKeyDown = (e: KeyboardEvent) => {
    if (e.key === "Enter") handleSubmit();
  };

  return (
    <AnimatePresence>
      {!isExiting ? (
        <motion.div
          className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-black"
          initial={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 1.2, ease: [0.25, 0.1, 0.25, 1] }}
        >
          <motion.div
            className="flex flex-col items-center"
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 1.2, delay: 0.4 }}
          >
            <h1 className="mb-3 font-mono text-sm tracking-[0.4em] text-white/60 uppercase">
              jbsh.me
            </h1>

            <p className="mb-14 text-xs tracking-[0.2em] text-white/30 uppercase">
              Access Required
            </p>

            <form onSubmit={handleSubmit} className="flex flex-col items-center">
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder=""
                autoFocus
                aria-label="Password"
                className={`w-64 bg-transparent text-center font-light text-white/90 outline-none transition-all duration-500 placeholder:text-white/20 ${
                  error ? "text-red-400/80" : ""
                }`}
                style={{
                  borderBottom: error
                    ? "1px solid rgba(248, 113, 113, 0.4)"
                    : "1px solid rgba(255, 255, 255, 0.15)",
                  paddingBottom: "12px",
                  fontSize: "16px",
                  letterSpacing: "0.15em",
                }}
              />

              <motion.button
                type="submit"
                className="mt-10 text-xs tracking-[0.3em] text-white/40 uppercase transition-colors hover:text-white/70"
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
              >
                Enter
              </motion.button>
            </form>
          </motion.div>
        </motion.div>
      ) : (
        <motion.div
          className="fixed inset-0 z-50 bg-black"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 1.2 }}
        />
      )}
    </AnimatePresence>
  );
}
