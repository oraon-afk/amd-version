"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { motion } from "framer-motion";
import { Building2, LockKeyhole, Mail, ShieldCheck, UserRound } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import type { ReactNode } from "react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useToast } from "@/components/ui/toast";
import { useAuth } from "@/providers/auth-provider";
import { getErrorMessage } from "@/services/api/client";

const schema = z
  .object({
    full_name: z.string().min(2, "Full name is required").max(255),
    email: z.string().email(),
    company_name: z.string().min(2, "Company name is required"),
    role: z.enum(["USER", "ADMIN"]),
    password: z.string().min(8).max(72).regex(/[A-Z]/, "Use at least one uppercase letter").regex(/[0-9]/, "Use at least one number"),
    confirm_password: z.string().min(8).max(72),
  })
  .refine((values) => values.password === values.confirm_password, {
    message: "Passwords do not match",
    path: ["confirm_password"],
  });

type FormValues = z.infer<typeof schema>;

export function RegisterForm() {
  const router = useRouter();
  const { register: registerAccount } = useAuth();
  const { toast } = useToast();
  const [error, setError] = useState<string | null>(null);
  const { register, handleSubmit, formState } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { role: "USER" },
  });

  async function onSubmit(values: FormValues) {
    setError(null);
    try {
      await registerAccount(values);
      toast({ title: "Account created", description: "You can now sign in to Audit AI." });
      router.push("/login");
    } catch (err) {
      const message = getErrorMessage(err);
      setError(message);
      toast({ title: "Registration failed", description: message, variant: "error" });
    }
  }

  return (
    <motion.form
      onSubmit={handleSubmit(onSubmit)}
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      className="glass-panel neon-border w-full max-w-2xl rounded-2xl p-7"
    >
      <div className="mb-7 text-center">
        <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-violet to-cyan shadow-glow">
          <ShieldCheck className="h-6 w-6 text-white" />
        </div>
        <h1 className="text-xl font-semibold">Create Your Account</h1>
        <p className="mt-2 text-sm text-muted">For teams that need auditable AI compliance workflows</p>
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        <Field icon={<UserRound />} label="Full name" error={formState.errors.full_name?.message}>
          <Input placeholder="Enter full name" {...register("full_name")} />
        </Field>
        <Field icon={<Mail />} label="Work email" error={formState.errors.email?.message}>
          <Input type="email" placeholder="name@company.com" {...register("email")} />
        </Field>
        <Field icon={<Building2 />} label="Company name" error={formState.errors.company_name?.message}>
          <Input placeholder="Company name" {...register("company_name")} />
        </Field>
        <Field label="Account role" error={formState.errors.role?.message}>
          <select
            {...register("role")}
            className="h-11 w-full rounded-lg border border-line bg-[#111827] px-3 text-sm outline-none focus:border-violet/70"
          >
            <option value="USER" className="bg-navy">User</option>
            <option value="ADMIN" className="bg-navy">Admin</option>
          </select>
        </Field>
        <Field icon={<LockKeyhole />} label="Password" error={formState.errors.password?.message}>
          <Input type="password" placeholder="Create password" {...register("password")} />
        </Field>
        <Field icon={<LockKeyhole />} label="Confirm password" error={formState.errors.confirm_password?.message}>
          <Input type="password" placeholder="Confirm password" {...register("confirm_password")} />
        </Field>
      </div>
      {error && <p className="mt-4 text-sm text-riskHigh">{error}</p>}
      <Button className="mt-6 w-full" disabled={formState.isSubmitting}>
        {formState.isSubmitting ? "Creating account" : "Create Account"}
      </Button>
      <p className="mt-5 text-center text-sm text-muted">
        Already have an account? <Link className="font-medium text-cyan" href="/login">Login</Link>
      </p>
    </motion.form>
  );
}

function Field({
  label,
  error,
  icon,
  children,
}: {
  label: string;
  error?: string;
  icon?: ReactNode;
  children: ReactNode;
}) {
  return (
    <label className="block text-sm font-medium">
      {label}
      <div className="relative mt-2">
        {icon && <span className="pointer-events-none absolute left-3 top-3 text-muted [&>svg]:h-4 [&>svg]:w-4">{icon}</span>}
        <div className={icon ? "[&>input]:pl-10" : undefined}>{children}</div>
      </div>
      {error && <span className="mt-1 block text-xs text-riskHigh">{error}</span>}
    </label>
  );
}
