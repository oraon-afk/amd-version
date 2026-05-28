import type { ReactNode } from "react";
import { ProtectedRoute } from "@/components/auth/ProtectedRoute";
import { AppShell } from "@/components/layout/AppShell";

export default function DashboardLayout({ children }: { children: ReactNode }) {
  return (
    <ProtectedRoute roles={["USER"]} redirectAdminToAdmin>
      <AppShell>{children}</AppShell>
    </ProtectedRoute>
  );
}
