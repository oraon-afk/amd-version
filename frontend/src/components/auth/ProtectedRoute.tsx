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
  const allowedRoles = useMemo(() => roles?.map((role) => role.toUpperCase()), [roles]);

  useEffect(() => {
    if (!isLoading && !user) router.push("/login");
    if (!isLoading && user && redirectAdminToAdmin && user.role === "ADMIN") router.replace("/admin");
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
