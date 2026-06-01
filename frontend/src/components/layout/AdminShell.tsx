"use client";

import {
  BarChart3,
  Database,
  FileClock,
  FileSearch,
  FileText,
  FolderUp,
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

const adminSections = [
  {
    label: "Dashboard",
    links: [{ href: "/admin", label: "Dashboard", icon: LayoutDashboard }],
  },
  {
    label: "Compliance Center",
    links: [
      { href: "/admin/compliance/upload", label: "Upload Audit Document", icon: FolderUp },
      { href: "/admin/compliance/bulk-upload", label: "Bulk Audit Upload", icon: FolderUp },
      { href: "/admin/compliance/audits", label: "Audit History", icon: FileClock },
      { href: "/admin/compliance/findings", label: "Findings", icon: ListChecks },
      { href: "/admin/compliance/evidence", label: "Evidence", icon: FileSearch },
      { href: "/admin/compliance/reports", label: "Reports", icon: ShieldCheck },
    ],
  },
  {
    label: "Rule Management",
    links: [
      { href: "/admin/rules", label: "Upload Rule", icon: FileText },
      { href: "/admin/rules/bulk-upload", label: "Bulk Rule Upload", icon: FolderUp },
      { href: "/admin/compliance-rules", label: "Rule Library", icon: ListChecks },
      { href: "/admin/rules/domains", label: "Domains", icon: Database },
      { href: "/admin/rules/versions", label: "Versions", icon: FileText },
    ],
  },
  {
    label: "Administration",
    links: [
      { href: "/admin/analytics", label: "Analytics", icon: BarChart3 },
      { href: "/admin/users", label: "Users", icon: Users },
      { href: "/admin/settings", label: "Settings", icon: Settings },
    ],
  },
];

export function AdminShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const { user, logout } = useAuth();

  return (
    <div className="min-h-screen bg-background bg-app-radial text-foreground">
      <aside className="fixed inset-y-0 left-0 z-30 hidden h-screen w-72 flex-col border-r border-line bg-panel/95 p-4 backdrop-blur-xl lg:flex">
        <div className="mb-7 flex shrink-0 items-center gap-3 px-2">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary shadow-glow">
            <ShieldCheck className="h-5 w-5 text-white" />
          </div>
          <div>
            <div className="text-sm font-semibold">Admin Console</div>
            <div className="text-xs text-muted">Policy Complice AI</div>
          </div>
        </div>
        <nav className="min-h-0 flex-1 space-y-5 overflow-y-auto pr-1 text-sm" aria-label="Administration navigation">
          {adminSections.map((section) => (
            <div key={section.label}>
              <div className="mb-2 px-3 text-[11px] font-semibold uppercase text-muted">{section.label}</div>
              <div className="space-y-1">
                {section.links.map((item) => (
                  <AdminNavLink
                    key={`${section.label}-${item.href}-${item.label}`}
                    href={item.href}
                    label={item.label}
                    icon={item.icon}
                    active={isActivePath(pathname, item.href)}
                  />
                ))}
              </div>
            </div>
          ))}
        </nav>
        <div className="mt-4 shrink-0 rounded-lg border border-line bg-elevated p-3">
          <div className="text-xs uppercase text-muted">Signed in as</div>
          <div className="mt-1 truncate text-sm font-semibold">{user?.full_name ?? user?.email}</div>
          <div className="mt-1 text-xs text-cyan">{user?.role}</div>
        </div>
      </aside>
      <div className="lg:pl-72">
        <header className="sticky top-0 z-20 flex h-16 items-center justify-between border-b border-line bg-background/86 px-4 backdrop-blur-xl md:px-6">
          <div>
            <div className="text-xs uppercase text-muted">Administration</div>
            <div className="text-sm font-semibold md:text-base">Rule Management, Compliance Checks, Users, and Storage</div>
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
        <div className="border-b border-line bg-panel/80 p-2 lg:hidden">
          <div className="flex gap-2 overflow-x-auto">
            {adminSections.flatMap((section) => section.links.map((item) => ({ ...item, section: section.label }))).map((item) => (
              <Link key={`${item.section}-${item.href}-${item.label}`} href={item.href} className="shrink-0 rounded-lg border border-line bg-elevated px-3 py-2 text-xs">
                {item.label}
              </Link>
            ))}
          </div>
        </div>
        <main className="p-4 md:p-6 xl:p-8">{children}</main>
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
        "flex items-center gap-3 rounded-lg px-3 py-2.5 text-muted transition hover:bg-elevated hover:text-foreground",
        active && "bg-primary/18 text-foreground shadow-[inset_3px_0_0_0_#60a5fa]",
      )}
      href={href}
    >
      <Icon className="h-4 w-4" /> {label}
    </Link>
  );
}

function isActivePath(pathname: string, href: string) {
  if (href === "/admin") return pathname === "/admin";
  if (href === "/admin/rules") return pathname === "/admin/rules";
  return pathname === href || pathname.startsWith(`${href}/`);
}
