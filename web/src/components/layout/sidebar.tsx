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
    <aside className="flex h-full w-[15rem] shrink-0 flex-col border-r border-border/80 bg-sidebar">
      <div className="flex h-[3.25rem] items-center gap-3 border-b border-border/80 px-5">
        <div className="flex h-8 w-8 items-center justify-center">
          <SeedIcon className="h-[1.125rem] w-[1.125rem] text-primary" />
        </div>
        <div>
          <p className="text-[0.9375rem] font-semibold tracking-[-0.02em] lowercase text-foreground">
            sedr
          </p>
          <p className="text-[0.625rem] font-medium tracking-wide text-muted-foreground/80 uppercase">
            Intelligence
          </p>
        </div>
      </div>
      <nav className="flex-1 space-y-0.5 overflow-y-auto p-2.5" aria-label="Main">
        {nav.map(({ href, label, icon: Icon }) => {
          const active =
            href === "/" ? pathname === "/" : pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-3 rounded-xl px-3 py-2.5 text-[0.875rem] transition-all duration-150",
                active
                  ? "bg-sidebar-accent font-medium text-sidebar-accent-foreground"
                  : "font-medium text-muted-foreground hover:bg-sidebar-accent/60 hover:text-foreground",
              )}
              aria-current={active ? "page" : undefined}
            >
              <Icon className="h-4 w-4 shrink-0 opacity-80" aria-hidden />
              {label}
            </Link>
          );
        })}
      </nav>
      <div className="border-t border-border/80 p-3">
        <button
          type="button"
          onClick={logout}
          className="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-[0.875rem] font-medium text-muted-foreground transition-colors duration-150 hover:bg-sidebar-accent/60 hover:text-foreground"
        >
          <LogOut className="h-4 w-4 shrink-0 opacity-80" aria-hidden />
          Log out
        </button>
      </div>
    </aside>
  );
}
