"use client";

import {
  FolderUp,
  LayoutDashboard,
  LogOut,
  ScrollText,
  Settings,
  ShieldCheck,
  type LucideIcon,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { ReactNode } from "react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useAuth } from "@/providers/auth-provider";

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const { user, logout } = useAuth();

  return (
    <div className="min-h-screen bg-background bg-app-radial text-foreground">
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-72 border-r border-line bg-panel/80 p-4 backdrop-blur-2xl lg:block">
        <div className="mb-7 flex items-center gap-3 px-2">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-violet to-cyan shadow-glow">
            <ShieldCheck className="h-5 w-5 text-white" />
          </div>
          <div>
            <div className="text-sm font-semibold">Audit AI</div>
            <div className="text-xs text-muted">Compliance Workspace</div>
          </div>
        </div>
        <nav className="space-y-1 text-sm">
          <NavLink href="/dashboard" label="Dashboard" icon={LayoutDashboard} active={pathname === "/dashboard"} />
          <NavLink href="/dashboard/upload" label="Upload Documents" icon={FolderUp} active={pathname === "/dashboard/upload"} />
          <NavLink href="/dashboard/reports" label="Audit Reports" icon={ScrollText} active={pathname.startsWith("/dashboard/reports")} />
          <NavLink href="/dashboard/settings" label="Settings" icon={Settings} active={pathname === "/dashboard/settings"} />
        </nav>
        <div className="absolute bottom-4 left-4 right-4 rounded-xl border border-line bg-white/5 p-3">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-gradient-to-br from-violet to-cyan text-sm font-bold">
              {(user?.full_name ?? user?.email ?? "U").slice(0, 1).toUpperCase()}
            </div>
            <div className="min-w-0">
              <div className="truncate text-sm font-semibold">{user?.full_name ?? user?.email ?? "User"}</div>
              <div className="truncate text-xs text-muted">{user?.role ?? "Authenticated user"}</div>
            </div>
          </div>
        </div>
      </aside>
      <div className="lg:pl-72">
        <header className="sticky top-0 z-20 flex h-16 items-center justify-between border-b border-line bg-background/72 px-4 backdrop-blur-2xl md:px-6">
          <div>
            <div className="text-xs uppercase tracking-[0.18em] text-muted">Enterprise Compliance Workspace</div>
            <div className="text-sm font-semibold md:text-base">AI Audit & Evidence Tracing</div>
          </div>
          <div className="flex items-center gap-3">
            <Button onClick={logout} variant="secondary" size="sm">
              <LogOut className="h-4 w-4" /> Sign out
            </Button>
          </div>
        </header>
        <main className="p-4 md:p-6">{children}</main>
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
        "flex items-center gap-3 rounded-lg px-3 py-2.5 text-muted transition hover:bg-white/8 hover:text-foreground",
        active && "bg-violet/18 text-foreground shadow-[inset_0_0_0_1px_rgba(168,85,247,0.28)]",
      )}
      href={href}
    >
      <Icon className="h-4 w-4" /> {label}
    </Link>
  );
}
