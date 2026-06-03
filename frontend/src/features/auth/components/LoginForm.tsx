"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { motion } from "framer-motion";
import { AlertCircle, ArrowRight, Eye, EyeOff, Loader2, LockKeyhole, Mail, ShieldCheck } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useToast } from "@/components/ui/toast";
import { useAuth } from "@/providers/auth-provider";
import { getErrorMessage } from "@/services/api/client";

const schema = z.object({
  email: z.string().email(),
  password: z.string().min(1).max(72),
  remember: z.boolean().optional(),
});

type FormValues = z.infer<typeof schema>;

export function LoginForm() {
  const router = useRouter();
  const { login } = useAuth();
  const { toast } = useToast();
  const [error, setError] = useState<string | null>(null);
  const [showPassword, setShowPassword] = useState(false);
  const { register, handleSubmit, formState } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { remember: true },
  });
  const emailError = formState.errors.email?.message;
  const passwordError = formState.errors.password?.message;

  async function onSubmit(values: FormValues) {
    setError(null);
    try {
      const user = await login(values);
      toast({ title: "Welcome back", description: "Secure workspace session restored." });
      router.push(user.role === "ADMIN" ? "/admin" : "/dashboard");
    } catch (err) {
      const message = getErrorMessage(err);
      setError(message);
      toast({ title: "Login failed", description: message, variant: "error" });
    }
  }

  return (
    <motion.form
      onSubmit={handleSubmit(onSubmit)}
      initial={false}
      animate={{ opacity: 1, y: 0 }}
      className="glass-panel w-full max-w-[31rem] rounded-lg p-6 sm:p-8"
    >
      <div className="mb-7 flex items-start gap-4">
        <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg bg-primary shadow-glow">
          <ShieldCheck className="h-6 w-6 text-white" />
        </div>
        <div>
          <p className="text-xs font-semibold uppercase text-info">Secure access</p>
          <h1 className="mt-1 text-2xl font-semibold">Login to your workspace</h1>
          <p className="mt-2 text-sm leading-6 text-muted">Resume document reviews, evidence checks, and report exports.</p>
        </div>
      </div>
      <div className="mb-6 grid grid-cols-3 gap-2 rounded-lg border border-line bg-elevated p-2 text-center text-[11px] text-muted">
        <div className="rounded-lg bg-card px-2 py-2">
          <span className="block text-sm font-semibold text-foreground">JWT</span>
          Session
        </div>
        <div className="rounded-lg bg-card px-2 py-2">
          <span className="block text-sm font-semibold text-riskLow">RBAC</span>
          Roles
        </div>
        <div className="rounded-lg bg-card px-2 py-2">
          <span className="block text-sm font-semibold text-riskMedium">Audit</span>
          Trace
        </div>
      </div>
      <label className="mb-4 block text-sm font-medium">
        Email address
        <div className="relative mt-2">
          <Mail className="pointer-events-none absolute left-3 top-3 h-4 w-4 text-muted" />
          <Input
            aria-describedby={emailError ? "login-email-error" : undefined}
            aria-invalid={!!emailError}
            autoComplete="email"
            className={`pl-10 ${emailError ? "border-riskHigh/70 focus:border-riskHigh/80" : ""}`}
            type="email"
            placeholder="name@company.com"
            {...register("email")}
          />
        </div>
        {emailError && (
          <span id="login-email-error" className="mt-1.5 flex items-center gap-1.5 text-xs text-riskHigh">
            <AlertCircle className="h-3.5 w-3.5" />
            {emailError}
          </span>
        )}
      </label>
      <label className="mb-3 block text-sm font-medium">
        Password
        <div className="relative mt-2">
          <LockKeyhole className="pointer-events-none absolute left-3 top-3 h-4 w-4 text-muted" />
          <Input
            aria-describedby={passwordError ? "login-password-error" : undefined}
            aria-invalid={!!passwordError}
            autoComplete="current-password"
            className={`pl-10 pr-11 ${passwordError ? "border-riskHigh/70 focus:border-riskHigh/80" : ""}`}
            type={showPassword ? "text" : "password"}
            placeholder="Enter your password"
            {...register("password")}
          />
          <button
            aria-label={showPassword ? "Hide password" : "Show password"}
            className="absolute right-2 top-1/2 flex h-8 w-8 -translate-y-1/2 items-center justify-center rounded-md text-muted transition hover:bg-elevated hover:text-foreground"
            type="button"
            onClick={() => setShowPassword((value) => !value)}
          >
            {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
          </button>
        </div>
        {passwordError && (
          <span id="login-password-error" className="mt-1.5 flex items-center gap-1.5 text-xs text-riskHigh">
            <AlertCircle className="h-3.5 w-3.5" />
            {passwordError}
          </span>
        )}
      </label>
      <div className="mb-5 flex items-center justify-between text-sm">
        <label className="flex items-center gap-2 text-muted">
          <input type="checkbox" className="h-4 w-4 accent-primary" {...register("remember")} />
          Remember me
        </label>
        <Link href="#" className="text-info hover:text-foreground">
          Forgot Password?
        </Link>
      </div>
      {error && <p className="mb-3 text-sm text-riskHigh">{error}</p>}
      <Button className="w-full" disabled={formState.isSubmitting} size="lg">
        {formState.isSubmitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <ArrowRight className="h-4 w-4" />}
        {formState.isSubmitting ? "Authenticating" : "Login"}
      </Button>
      <p className="mt-5 text-center text-sm text-muted">
        Don&apos;t have an account? <Link className="font-medium text-info hover:text-foreground" href="/register">Create one</Link>
      </p>
    </motion.form>
  );
}
