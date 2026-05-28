"use client";

import { useQuery } from "@tanstack/react-query";
import { Users } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { getErrorMessage } from "@/services/api/client";
import { listAdminUsers } from "@/services/admin/admin-service";
import { formatDate } from "@/lib/utils";

export default function AdminUsersPage() {
  const usersQuery = useQuery({ queryKey: ["admin-users"], queryFn: listAdminUsers });

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-semibold">Users</h1>
        <p className="mt-1 text-sm text-muted">Registered ADMIN and USER accounts.</p>
      </div>
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>All Users</CardTitle>
          <Users className="h-5 w-5 text-cyan" />
        </CardHeader>
        <CardContent className="space-y-3">
          {usersQuery.isLoading && <Skeleton className="h-32 w-full" />}
          {usersQuery.error && <p className="text-sm text-riskHigh">{getErrorMessage(usersQuery.error)}</p>}
          {usersQuery.data?.map((user) => (
            <div key={user.id} className="grid gap-3 rounded-lg border border-line bg-white/5 p-4 text-sm md:grid-cols-[1fr_180px_160px]">
              <div className="min-w-0">
                <div className="truncate font-semibold">{user.full_name ?? user.email}</div>
                <div className="mt-1 truncate text-xs text-muted">{user.email}</div>
              </div>
              <Badge variant={user.role === "ADMIN" ? "cyan" : "muted"}>{user.role}</Badge>
              <div className="text-xs text-muted">{formatDate(user.created_at)}</div>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
