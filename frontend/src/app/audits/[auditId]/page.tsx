import { redirect } from "next/navigation";

type AuditAliasPageProps = {
  params: Promise<{ auditId: string }>;
};

export default async function AuditAliasPage({ params }: AuditAliasPageProps) {
  const { auditId } = await params;
  redirect(`/dashboard/reports/${auditId}`);
}
