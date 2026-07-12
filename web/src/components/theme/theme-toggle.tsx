"use client";

import { Moon, Sun } from "lucide-react";
import { useTheme } from "@/components/providers/theme-provider";
import { Switch } from "@/components/ui/switch";
import { cn } from "@/lib/utils";

type ThemeToggleProps = {
  className?: string;
  showLabel?: boolean;
};

export function ThemeToggle({ className, showLabel = false }: ThemeToggleProps) {
  const { theme, setTheme, mounted } = useTheme();
  const isDark = theme === "dark";

  if (!mounted) {
    return <div className={cn("h-[18px] w-8", className)} aria-hidden />;
  }

  return (
    <div
      className={cn(
        "flex items-center gap-2.5",
        className,
      )}
    >
      <Sun
        className={cn(
          "h-3.5 w-3.5 transition-colors duration-200",
          isDark ? "text-muted-foreground/40" : "text-foreground/70",
        )}
        aria-hidden
      />
      <Switch
        checked={isDark}
        onCheckedChange={(checked) => setTheme(checked ? "dark" : "light")}
        aria-label={isDark ? "Switch to light mode" : "Switch to dark mode"}
        className="data-checked:bg-primary data-unchecked:bg-input/80"
      />
      <Moon
        className={cn(
          "h-3.5 w-3.5 transition-colors duration-200",
          isDark ? "text-foreground/70" : "text-muted-foreground/40",
        )}
        aria-hidden
      />
      {showLabel && (
        <span className="text-sm text-muted-foreground">
          {isDark ? "Dark" : "Light"}
        </span>
      )}
    </div>
  );
}
