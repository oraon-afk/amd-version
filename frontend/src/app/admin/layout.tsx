import type { ReactNode } from "react";
import { ProtectedRoute } from "@/components/auth/ProtectedRoute";
import { AdminShell } from "@/components/layout/AdminShell";

export default function AdminLayout({ children }: { children: ReactNode }) {
  return (
    <ProtectedRoute roles={["ADMIN"]}>
      <AdminShell>{children}</AdminShell>
    </ProtectedRoute>
  );
}
