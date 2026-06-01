"use client";

import { useQuery } from "@tanstack/react-query";
import { Users } from "lucide-react";
import { DataTable, type DataTableColumn } from "@/components/enterprise/DataTable";
import { StatusBadge } from "@/components/enterprise/StatusBadge";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { getErrorMessage } from "@/services/api/client";
import { listAdminUsers } from "@/services/admin/admin-service";
import { formatDate } from "@/lib/utils";
import { User } from "@/types/api";

export default function AdminUsersPage() {
  const usersQuery = useQuery({ queryKey: ["admin-users"], queryFn: listAdminUsers });
  const users = usersQuery.data ?? [];
  const columns: DataTableColumn<User>[] = [
    {
      id: "user",
      header: "User",
      cell: (user) => (
        <div className="min-w-0">
          <div className="truncate font-semibold">{user.full_name ?? user.email}</div>
          <div className="mt-1 truncate text-xs text-muted">{user.email}</div>
        </div>
      ),
      sortValue: (user) => user.full_name ?? user.email,
      searchValue: (user) => `${user.full_name ?? ""} ${user.email}`,
    },
    {
      id: "role",
      header: "Role",
      cell: (user) => <Badge variant={user.role === "ADMIN" ? "cyan" : "muted"}>{user.role}</Badge>,
      sortValue: (user) => user.role,
    },
    {
      id: "status",
      header: "Status",
      cell: (user) => <StatusBadge status={user.is_active ? "completed" : "failed"} label={user.is_active ? "Active" : "Inactive"} />,
      sortValue: (user) => (user.is_active ? "Active" : "Inactive"),
    },
    {
      id: "created",
      header: "Created",
      cell: (user) => <span className="text-muted">{formatDate(user.created_at)}</span>,
      sortValue: (user) => user.created_at ?? "",
      exportValue: (user) => formatDate(user.created_at),
    },
  ];

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
          {users.length > 0 && (
            <DataTable
              data={users}
              columns={columns}
              getRowId={(user) => user.id}
              searchPlaceholder="Search users by name, email, or role"
              exportFilename="admin-users.csv"
              filters={[
                { id: "admins", label: "Admins", predicate: (user) => user.role === "ADMIN" },
                { id: "users", label: "Users", predicate: (user) => user.role !== "ADMIN" },
                { id: "active", label: "Active", predicate: (user) => user.is_active },
              ]}
            />
          )}
        </CardContent>
      </Card>
    </div>
  );
}
