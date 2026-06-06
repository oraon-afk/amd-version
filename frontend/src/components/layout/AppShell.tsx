"use client";

import {
  ClipboardList,
  Gauge,
  FolderUp,
  LayoutDashboard,
  ListChecks,
  LogOut,
  ScrollText,
  Settings,
  ShieldCheck,
  Sparkles,
  type LucideIcon,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { ReactNode } from "react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useAuth } from "@/providers/auth-provider";
import { CosmicBackground } from "./CosmicBackground";

const workspaceSections = [
  {
    label: "Dashboard",
    links: [{ href: "/dashboard", label: "Dashboard", icon: LayoutDashboard }],
  },
  {
    label: "Compliance Check",
    links: [
      { href: "/dashboard/upload", label: "Upload Document", icon: FolderUp },
      { href: "/dashboard/bulk-upload", label: "Bulk Upload", icon: FolderUp },
      { href: "/dashboard/audits", label: "Audit History", icon: ClipboardList },
      { href: "/dashboard/violations", label: "Findings", icon: ListChecks },
      { href: "/dashboard/evidence", label: "Evidence", icon: ShieldCheck },
      { href: "/dashboard/reports", label: "Reports", icon: ScrollText },
    ],
  },
  {
    label: "Digital Twin",
    links: [{ href: "/dashboard/digital-twin", label: "Compliance Twin", icon: Gauge }],
  },
  {
    label: "Settings",
    links: [{ href: "/dashboard/settings", label: "Settings", icon: Settings }],
  },
];

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const { user, logout } = useAuth();

  return (
    <div className="relative min-h-screen bg-background bg-app-radial text-foreground">
      <CosmicBackground />
      <aside className="fixed inset-y-0 left-0 z-30 hidden h-screen w-72 flex-col border-r border-line bg-panel/95 p-4 backdrop-blur-xl lg:flex antigravity-float-slow">
        <div className="mb-7 flex shrink-0 items-center gap-3 px-2">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary shadow-glow">
            <ShieldCheck className="h-5 w-5 text-white" />
          </div>
          <div>
            <div className="text-sm font-semibold">Policy Complice AI</div>
            <div className="text-xs text-muted">Compliance Intelligence</div>
          </div>
        </div>
        <nav className="min-h-0 flex-1 space-y-5 overflow-y-auto pr-1 text-sm" aria-label="Workspace navigation">
          {workspaceSections.map((section) => (
            <div key={section.label}>
              <div className="mb-2 px-3 text-[11px] font-semibold uppercase text-muted">{section.label}</div>
              <div className="space-y-1">
                {section.links.map((item) => (
                  <NavLink
                    key={item.href}
                    href={item.href}
                    label={item.label}
                    icon={item.icon}
                    active={item.href === "/dashboard" ? pathname === "/dashboard" : pathname.startsWith(item.href)}
                  />
                ))}
              </div>
            </div>
          ))}
        </nav>
        <div className="mt-4 shrink-0 rounded-lg border border-line bg-elevated p-3 antigravity-float-alt">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-navy text-sm font-bold text-info">
              {(user?.full_name ?? user?.email ?? "U").slice(0, 1).toUpperCase()}
            </div>
            <div className="min-w-0">
              <div className="truncate text-sm font-semibold">{user?.full_name ?? user?.email ?? "User"}</div>
              <div className="truncate text-xs text-muted">{user?.role ?? "Authenticated user"}</div>
            </div>
          </div>
        </div>
      </aside>
      <div className="relative z-10 lg:pl-72">
        <header className="sticky top-0 z-20 flex min-h-16 flex-wrap items-center justify-between gap-3 border-b border-line bg-background/86 px-4 py-3 backdrop-blur-xl md:px-6">
          <div className="min-w-0">
            <div className="text-xs uppercase text-muted">Enterprise Compliance Workspace</div>
            <div className="flex min-w-0 items-center gap-2 text-sm font-semibold md:text-base">
              <Sparkles className="h-4 w-4 text-info" /> Policy Review & Evidence Tracing
            </div>
          </div>
          <div className="flex items-center gap-3">
            <Button onClick={logout} variant="secondary" size="sm">
              <LogOut className="h-4 w-4" /> Sign out
            </Button>
          </div>
        </header>
        <div className="border-b border-line bg-panel/80 p-2 lg:hidden">
          <div className="flex gap-2 overflow-x-auto">
            {workspaceSections.flatMap((section) => section.links).map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "shrink-0 rounded-lg border border-line bg-elevated px-3 py-2 text-xs text-muted",
                  (item.href === "/dashboard" ? pathname === "/dashboard" : pathname.startsWith(item.href)) && "border-info/40 bg-primary/20 text-foreground",
                )}
              >
                {item.label}
              </Link>
            ))}
          </div>
        </div>
        <main className="min-w-0 p-4 md:p-6 xl:p-8">{children}</main>
      </div>
    </div>
  );
}

function NavLink({
  href,
  label,
  icon: Icon,
  active,
}: {
  href: string;
  label: string;
  icon: LucideIcon;
  active: boolean;
}) {
  return (
    <Link
      className={cn(
        "flex items-center gap-3 rounded-lg px-3 py-2.5 text-muted transition hover:bg-elevated hover:text-foreground",
        active && "bg-primary/18 text-foreground shadow-[inset_3px_0_0_0_#7C4DFF]",
      )}
      href={href}
    >
      <Icon className="h-4 w-4" /> {label}
    </Link>
  );
}
