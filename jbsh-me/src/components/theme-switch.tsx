"use client";

import { motion } from "framer-motion";
import { useTheme } from "@/components/providers/theme-provider";

/**
 * A tiny iPhone-style sliding switch. Almost disappears into the interface.
 * Left is light, right is dark.
 */
export function ThemeSwitch() {
  const { resolvedTheme, setTheme } = useTheme();
  const isDark = resolvedTheme === "dark";

  return (
    <button
      onClick={() => setTheme(isDark ? "light" : "dark")}
      className="fixed top-6 right-6 z-50 flex h-[22px] w-[38px] items-center rounded-full border border-foreground/10 bg-foreground/[0.06] px-[3px] backdrop-blur-md transition-colors hover:bg-foreground/10"
      style={{ justifyContent: isDark ? "flex-end" : "flex-start" }}
      role="switch"
      aria-checked={isDark}
      aria-label="Toggle dark mode"
    >
      <motion.span
        layout
        transition={{ type: "spring", stiffness: 500, damping: 34 }}
        className="h-[16px] w-[16px] rounded-full bg-foreground shadow-sm"
      />
    </button>
  );
}
