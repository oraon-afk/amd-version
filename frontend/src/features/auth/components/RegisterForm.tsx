"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { motion } from "framer-motion";
import {
  AlertCircle,
  ArrowRight,
  BadgeCheck,
  Building2,
  Eye,
  EyeOff,
  Loader2,
  LockKeyhole,
  Mail,
  ShieldCheck,
  UserRound,
  UsersRound,
} from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import type { ReactNode } from "react";
import { useState } from "react";
import { type UseFormRegister, useForm } from "react-hook-form";
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
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const { register, handleSubmit, formState, watch } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { role: "USER" },
  });
  const password = watch("password") ?? "";
  const passwordChecks = [
    { label: "8+ characters", valid: password.length >= 8 },
    { label: "Uppercase", valid: /[A-Z]/.test(password) },
    { label: "Number", valid: /[0-9]/.test(password) },
  ];

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
      initial={false}
      animate={{ opacity: 1, y: 0 }}
      className="glass-panel neon-border w-full max-w-2xl rounded-2xl p-6 sm:p-8"
    >
      <div className="mb-7 flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex items-start gap-4">
          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-gradient-to-br from-violet to-cyan shadow-glow">
            <ShieldCheck className="h-6 w-6 text-white" />
          </div>
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-cyan">Team onboarding</p>
            <h1 className="mt-1 text-2xl font-semibold">Create your account</h1>
            <p className="mt-2 max-w-md text-sm leading-6 text-muted">Set up access for compliance review, evidence tracing, and report workflows.</p>
          </div>
        </div>
        <div className="flex w-fit items-center gap-2 rounded-xl border border-riskLow/25 bg-riskLow/10 px-3 py-2 text-xs text-riskLow">
          <BadgeCheck className="h-4 w-4" />
          First account becomes admin
        </div>
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        <Field icon={<UserRound />} label="Full name" error={formState.errors.full_name?.message}>
          <Input
            aria-invalid={!!formState.errors.full_name}
            autoComplete="name"
            className={formState.errors.full_name ? "border-riskHigh/70 focus:border-riskHigh/80" : undefined}
            placeholder="Enter full name"
            {...register("full_name")}
          />
        </Field>
        <Field icon={<Mail />} label="Work email" error={formState.errors.email?.message}>
          <Input
            aria-invalid={!!formState.errors.email}
            autoComplete="email"
            className={formState.errors.email ? "border-riskHigh/70 focus:border-riskHigh/80" : undefined}
            type="email"
            placeholder="name@company.com"
            {...register("email")}
          />
        </Field>
        <Field icon={<Building2 />} label="Company name" error={formState.errors.company_name?.message}>
          <Input
            aria-invalid={!!formState.errors.company_name}
            autoComplete="organization"
            className={formState.errors.company_name ? "border-riskHigh/70 focus:border-riskHigh/80" : undefined}
            placeholder="Company name"
            {...register("company_name")}
          />
        </Field>
        <RoleField error={formState.errors.role?.message} register={register} />
        <Field icon={<LockKeyhole />} label="Password" error={formState.errors.password?.message}>
          <Input
            aria-invalid={!!formState.errors.password}
            autoComplete="new-password"
            className={`pr-11 ${formState.errors.password ? "border-riskHigh/70 focus:border-riskHigh/80" : ""}`}
            type={showPassword ? "text" : "password"}
            placeholder="Create password"
            {...register("password")}
          />
          <PasswordToggle show={showPassword} onClick={() => setShowPassword((value) => !value)} />
        </Field>
        <Field icon={<LockKeyhole />} label="Confirm password" error={formState.errors.confirm_password?.message}>
          <Input
            aria-invalid={!!formState.errors.confirm_password}
            autoComplete="new-password"
            className={`pr-11 ${formState.errors.confirm_password ? "border-riskHigh/70 focus:border-riskHigh/80" : ""}`}
            type={showConfirmPassword ? "text" : "password"}
            placeholder="Confirm password"
            {...register("confirm_password")}
          />
          <PasswordToggle show={showConfirmPassword} onClick={() => setShowConfirmPassword((value) => !value)} />
        </Field>
        <div className="md:col-span-2">
          <div className="grid gap-2 rounded-xl border border-line bg-white/5 p-3 text-xs text-muted sm:grid-cols-3">
            {passwordChecks.map((check) => (
              <div key={check.label} className="flex items-center gap-2">
                <span className={`h-2 w-2 rounded-full ${check.valid ? "bg-riskLow" : "bg-muted/40"}`} />
                <span className={check.valid ? "text-foreground" : undefined}>{check.label}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
      {error && <p className="mt-4 text-sm text-riskHigh">{error}</p>}
      <Button className="mt-6 w-full" disabled={formState.isSubmitting} size="lg">
        {formState.isSubmitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <ArrowRight className="h-4 w-4" />}
        {formState.isSubmitting ? "Creating account" : "Create account"}
      </Button>
      <p className="mt-5 text-center text-sm text-muted">
        Already have an account? <Link className="font-medium text-cyan hover:text-foreground" href="/login">Login</Link>
      </p>
    </motion.form>
  );
}

function RoleField({
  error,
  register,
}: {
  error?: string;
  register: UseFormRegister<FormValues>;
}) {
  return (
    <div className="block text-sm font-medium">
      Account role
      <div className="mt-2 grid grid-cols-2 gap-2">
        <label className="cursor-pointer">
          <input type="radio" value="USER" className="peer sr-only" {...register("role")} />
          <span className="flex h-full items-center gap-3 rounded-lg border border-line bg-white/6 px-3 py-2 text-sm text-muted transition peer-checked:border-cyan/70 peer-checked:bg-cyan/10 peer-checked:text-foreground">
            <UsersRound className="h-4 w-4 text-cyan" />
            User
          </span>
        </label>
        <label className="cursor-pointer">
          <input type="radio" value="ADMIN" className="peer sr-only" {...register("role")} />
          <span className="flex h-full items-center gap-3 rounded-lg border border-line bg-white/6 px-3 py-2 text-sm text-muted transition peer-checked:border-riskMedium/70 peer-checked:bg-riskMedium/10 peer-checked:text-foreground">
            <ShieldCheck className="h-4 w-4 text-riskMedium" />
            Admin
          </span>
        </label>
      </div>
      {error && (
        <span className="mt-1.5 flex items-center gap-1.5 text-xs text-riskHigh">
          <AlertCircle className="h-3.5 w-3.5" />
          {error}
        </span>
      )}
    </div>
  );
}

function PasswordToggle({ show, onClick }: { show: boolean; onClick: () => void }) {
  return (
    <button
      aria-label={show ? "Hide password" : "Show password"}
      className="absolute right-2 top-1/2 flex h-8 w-8 -translate-y-1/2 items-center justify-center rounded-md text-muted transition hover:bg-white/8 hover:text-foreground"
      type="button"
      onClick={onClick}
    >
      {show ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
    </button>
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
      {error && (
        <span className="mt-1.5 flex items-center gap-1.5 text-xs text-riskHigh">
          <AlertCircle className="h-3.5 w-3.5" />
          {error}
        </span>
      )}
    </label>
  );
}
