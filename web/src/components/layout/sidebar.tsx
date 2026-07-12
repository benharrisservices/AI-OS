"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Bot,
  Brain,
  CalendarClock,
  Cpu,
  Download,
  Home,
  Layers,
  LogOut,
  Plug,
  Scale,
  Settings,
  Workflow,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { SeedIcon } from "@/components/brand/seed-icon";
import { logout } from "@/lib/auth";

const nav = [
  { href: "/", label: "Dashboard", icon: Home },
  { href: "/knowledge", label: "Knowledge", icon: Layers },
  { href: "/memory", label: "Memory", icon: Brain },
  { href: "/decisions", label: "Decisions", icon: Scale },
  { href: "/agents", label: "Agents", icon: Bot },
  { href: "/workflows", label: "Workflows", icon: Workflow },
  { href: "/automations", label: "Automations", icon: CalendarClock },
  { href: "/imports", label: "Imports", icon: Download },
  { href: "/providers", label: "Providers", icon: Plug },
  { href: "/models", label: "Models", icon: Cpu },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="flex h-full w-[16.5rem] shrink-0 flex-col border-r border-border/70 bg-sidebar">
      <div className="flex h-[3.5rem] items-center gap-3 border-b border-border/70 px-5">
        <div className="flex h-8 w-8 items-center justify-center">
          <SeedIcon className="h-[1.25rem] w-[1.25rem] text-primary" />
        </div>
        <div>
          <p className="text-[1rem] font-bold tracking-[-0.02em] lowercase text-foreground">
            sedr
          </p>
          <p className="text-[0.6875rem] font-semibold tracking-[0.06em] text-muted-foreground uppercase">
            Intelligence
          </p>
        </div>
      </div>
      <nav className="flex-1 space-y-1 overflow-y-auto p-3" aria-label="Main">
        {nav.map(({ href, label, icon: Icon }) => {
          const active =
            href === "/" ? pathname === "/" : pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-3 rounded-xl px-3.5 py-3 text-[0.9688rem] font-semibold transition-all duration-150 ease-out",
                active
                  ? "nav-selected text-foreground"
                  : "text-muted-foreground hover:bg-sidebar-accent/70 hover:text-foreground",
              )}
              aria-current={active ? "page" : undefined}
            >
              <Icon
                className={cn(
                  "h-[1.125rem] w-[1.125rem] shrink-0 transition-opacity",
                  active ? "text-primary opacity-100" : "opacity-80",
                )}
                strokeWidth={active ? 2.4 : 2.1}
                aria-hidden
              />
              {label}
            </Link>
          );
        })}
      </nav>
      <div className="border-t border-border/70 p-3">
        <button
          type="button"
          onClick={logout}
          className="flex w-full items-center gap-3 rounded-xl px-3.5 py-3 text-[0.9688rem] font-semibold text-muted-foreground transition-colors duration-150 ease-out hover:bg-sidebar-accent/70 hover:text-foreground"
        >
          <LogOut className="h-[1.125rem] w-[1.125rem] shrink-0 opacity-80" strokeWidth={2.1} aria-hidden />
          Log out
        </button>
      </div>
    </aside>
  );
}
