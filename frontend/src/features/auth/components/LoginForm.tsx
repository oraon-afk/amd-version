"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { motion } from "framer-motion";
import { Eye, LockKeyhole, Mail, ShieldCheck } from "lucide-react";
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
  const { register, handleSubmit, formState } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { remember: true },
  });

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
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      className="glass-panel neon-border w-full max-w-md rounded-2xl p-7"
    >
      <div className="mb-7 text-center">
        <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-violet to-cyan shadow-glow">
          <ShieldCheck className="h-6 w-6 text-white" />
        </div>
        <h1 className="text-xl font-semibold">Login to Your Account</h1>
        <p className="mt-2 text-sm text-muted">Enter your credentials to access your workspace</p>
      </div>
      <label className="mb-4 block text-sm font-medium">
        Email address
        <div className="relative mt-2">
          <Mail className="pointer-events-none absolute left-3 top-3 h-4 w-4 text-muted" />
          <Input className="pl-10" type="email" placeholder="Enter your email" {...register("email")} />
        </div>
      </label>
      <label className="mb-3 block text-sm font-medium">
        Password
        <div className="relative mt-2">
          <LockKeyhole className="pointer-events-none absolute left-3 top-3 h-4 w-4 text-muted" />
          <Input className="pl-10 pr-10" type="password" placeholder="Enter your password" {...register("password")} />
          <Eye className="pointer-events-none absolute right-3 top-3 h-4 w-4 text-muted" />
        </div>
      </label>
      <div className="mb-5 flex items-center justify-between text-sm">
        <label className="flex items-center gap-2 text-muted">
          <input type="checkbox" className="h-4 w-4 accent-violet" {...register("remember")} />
          Remember me
        </label>
        <Link href="#" className="text-cyan hover:text-foreground">
          Forgot Password?
        </Link>
      </div>
      {error && <p className="mb-3 text-sm text-riskHigh">{error}</p>}
      <Button className="w-full" disabled={formState.isSubmitting}>
        {formState.isSubmitting ? "Authenticating" : "Login"}
      </Button>
      <p className="mt-5 text-center text-sm text-muted">
        Don&apos;t have an account? <Link className="font-medium text-cyan" href="/register">Create one</Link>
      </p>
    </motion.form>
  );
}
