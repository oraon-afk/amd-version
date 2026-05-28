"use client";

import {
  BarChart3,
  Database,
  FileClock,
  FileText,
  LayoutDashboard,
  ListChecks,
  LogOut,
  Settings,
  ShieldCheck,
  Users,
  type LucideIcon,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { ReactNode } from "react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useAuth } from "@/providers/auth-provider";

const adminLinks = [
  { href: "/admin", label: "Dashboard", icon: LayoutDashboard },
  { href: "/admin/users", label: "Users", icon: Users },
  { href: "/admin/rules", label: "Rule Documents", icon: FileText },
  { href: "/admin/reports", label: "Audit Reports", icon: FileClock },
  { href: "/admin/compliance-rules", label: "Compliance Rules", icon: ListChecks },
  { href: "/admin/analytics", label: "Analytics", icon: BarChart3 },
  { href: "/admin/settings", label: "Settings", icon: Settings },
];

export function AdminShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const { user, logout } = useAuth();

  return (
    <div className="min-h-screen bg-background bg-app-radial text-foreground">
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-72 border-r border-line bg-panel/85 p-4 backdrop-blur-2xl lg:block">
        <div className="mb-7 flex items-center gap-3 px-2">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-to-br from-violet to-cyan shadow-glow">
            <ShieldCheck className="h-5 w-5 text-white" />
          </div>
          <div>
            <div className="text-sm font-semibold">Admin Console</div>
            <div className="text-xs text-muted">Audit AI Controls</div>
          </div>
        </div>
        <nav className="space-y-1 text-sm">
          {adminLinks.map((item) => (
            <AdminNavLink
              key={item.href}
              href={item.href}
              label={item.label}
              icon={item.icon}
              active={item.href === "/admin" ? pathname === "/admin" : pathname.startsWith(item.href)}
            />
          ))}
        </nav>
        <div className="absolute bottom-4 left-4 right-4 rounded-lg border border-line bg-white/5 p-3">
          <div className="text-xs uppercase text-muted">Signed in as</div>
          <div className="mt-1 truncate text-sm font-semibold">{user?.full_name ?? user?.email}</div>
          <div className="mt-1 text-xs text-cyan">{user?.role}</div>
        </div>
      </aside>
      <div className="lg:pl-72">
        <header className="sticky top-0 z-20 flex h-16 items-center justify-between border-b border-line bg-background/72 px-4 backdrop-blur-2xl md:px-6">
          <div>
            <div className="text-xs uppercase tracking-[0.18em] text-muted">Administration</div>
            <div className="text-sm font-semibold md:text-base">Rules, Users, Storage, and Audit History</div>
          </div>
          <div className="flex items-center gap-2">
            <Link href="/admin/rules">
              <Button variant="secondary" size="sm">
                <Database className="h-4 w-4" /> Rule Upload
              </Button>
            </Link>
            <Button onClick={logout} variant="secondary" size="sm">
              <LogOut className="h-4 w-4" /> Sign out
            </Button>
          </div>
        </header>
        <div className="border-b border-line bg-panel/50 p-2 lg:hidden">
          <div className="flex gap-2 overflow-x-auto">
            {adminLinks.map((item) => (
              <Link key={item.href} href={item.href} className="shrink-0 rounded-lg border border-line bg-white/5 px-3 py-2 text-xs">
                {item.label}
              </Link>
            ))}
          </div>
        </div>
        <main className="p-4 md:p-6">{children}</main>
      </div>
    </div>
  );
}

function AdminNavLink({
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
        active && "bg-cyan/12 text-foreground shadow-[inset_0_0_0_1px_rgba(56,189,248,0.28)]",
      )}
      href={href}
    >
      <Icon className="h-4 w-4" /> {label}
    </Link>
  );
}
