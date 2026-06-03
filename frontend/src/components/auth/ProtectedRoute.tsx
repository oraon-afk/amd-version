"use client";

import { useRouter } from "next/navigation";
import { ReactNode, useEffect, useMemo } from "react";
import { Skeleton } from "@/components/ui/skeleton";
import { useAuth } from "@/providers/auth-provider";

export function ProtectedRoute({
  children,
  roles,
  redirectAdminToAdmin = false,
}: {
  children: ReactNode;
  roles?: string[];
  redirectAdminToAdmin?: boolean;
}) {
  const router = useRouter();
  const { user, isLoading } = useAuth();
  const roleKey = roles?.join("|") ?? "";
  const allowedRoles = useMemo(() => (roleKey ? roleKey.split("|").map((role) => role.toUpperCase()) : undefined), [roleKey]);

  useEffect(() => {
    if (isLoading) return;
    if (!user) {
      router.push("/login");
      return;
    }
    if (redirectAdminToAdmin && user.role === "ADMIN") {
      router.replace("/admin");
      return;
    }
    if (!isLoading && user && allowedRoles && !allowedRoles.includes(user.role.toUpperCase())) {
      router.replace(user.role === "ADMIN" ? "/admin" : "/dashboard");
    }
  }, [allowedRoles, isLoading, redirectAdminToAdmin, router, user]);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-background p-6">
        <Skeleton className="mb-4 h-12 w-64" />
        <Skeleton className="h-[70vh] w-full" />
      </div>
    );
  }

  if (!user) return null;
  if (allowedRoles && !allowedRoles.includes(user.role.toUpperCase())) return null;
  if (redirectAdminToAdmin && user.role === "ADMIN") return null;
  return <>{children}</>;
}
