"use client";

import { motion } from "framer-motion";
import { CheckCircle2, Clock3, FileCheck2, Radar, ShieldCheck, Sparkles, type LucideIcon } from "lucide-react";

export function AuthShowcase({ mode }: { mode: "login" | "register" }) {
  const metrics =
    mode === "login"
      ? [
          { label: "Open audits", value: "12" },
          { label: "Citations traced", value: "98%" },
          { label: "Reports ready", value: "4" },
        ]
      : [
          { label: "Setup time", value: "2m" },
          { label: "Roles", value: "2" },
          { label: "Audit trail", value: "On" },
        ];

  return (
    <section className="relative z-10 hidden overflow-hidden border-r border-line bg-panel p-10 lg:block">
      <div className="relative z-10 flex h-full flex-col justify-between">
        <div>
          <div className="mb-8 flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-lg bg-primary shadow-glow">
              <ShieldCheck className="h-5 w-5 text-white" />
            </div>
            <div>
              <div className="font-semibold">Policy Complice AI</div>
              <div className="text-xs text-muted">Enterprise compliance intelligence</div>
            </div>
          </div>
          <h2 className="max-w-md text-4xl font-semibold leading-tight">
            {mode === "login" ? "Secure compliance intelligence for audit-ready teams." : "Create an enterprise compliance workspace."}
          </h2>
          <p className="mt-4 max-w-md text-sm leading-6 text-muted">
            Validate documents, trace citations, surface violations, and generate executive-ready reports with grounded AI.
          </p>
          <div className="mt-6 grid max-w-md grid-cols-3 gap-3">
            {metrics.map((metric) => (
              <div key={metric.label} className="rounded-lg border border-line bg-elevated p-3">
                <div className="text-lg font-semibold text-foreground">{metric.value}</div>
                <div className="mt-1 text-[11px] text-muted">{metric.label}</div>
              </div>
            ))}
          </div>
        </div>
        <motion.div
          initial={false}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.15 }}
          className="glass-panel antigravity-float relative mx-auto aspect-square w-[360px] rounded-2xl p-8"
        >
          <div className="absolute inset-8 rounded-[1.5rem] border border-primary/20 bg-primary/10" />
          <div className="absolute left-8 right-8 top-8 rounded-2xl border border-line bg-panel/80 p-3 text-xs text-muted">
            <div className="mb-2 flex items-center justify-between">
              <span>Policy packet</span>
              <span className="text-riskLow">Verified</span>
            </div>
            <div className="h-1.5 overflow-hidden rounded-full bg-white/10">
              <motion.div
                animate={{ width: ["48%", "86%", "68%"] }}
                transition={{ duration: 5, repeat: Infinity, repeatType: "mirror" }}
                className="h-full rounded-full bg-gradient-to-r from-violet to-cyan"
              />
            </div>
          </div>
          <div className="absolute left-1/2 top-1/2 flex h-28 w-28 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-2xl bg-primary shadow-glow">
            <ShieldCheck className="h-12 w-12 text-white" />
          </div>
          <FloatingLabel icon={FileCheck2} label="Validation" x={20} y={28} delay={0.2} />
          <FloatingLabel icon={Radar} label="Rules" x={66} y={18} delay={0.66} />
          <FloatingLabel icon={Sparkles} label="Reports" x={68} y={68} delay={0.68} />
          <FloatingLabel icon={ShieldCheck} label="Controls" x={16} y={72} delay={0.16} />
        </motion.div>
        <div className="grid grid-cols-2 gap-3 text-sm">
          <ShowcaseTile icon={FileCheck2} label="Document upload" />
          <ShowcaseTile icon={Radar} label="Rule retrieval" />
          <ShowcaseTile icon={Clock3} label="LLM analysis" />
          <ShowcaseTile icon={CheckCircle2} label="Report export" />
        </div>
      </div>
    </section>
  );
}

function ShowcaseTile({ icon: Icon, label }: { icon: LucideIcon; label: string }) {
  return (
    <div className="flex items-center gap-3 rounded-lg border border-line bg-elevated p-3 text-muted">
      <Icon className="h-4 w-4 text-cyan" />
      {label}
    </div>
  );
}

function FloatingLabel({
  icon: Icon,
  label,
  x,
  y,
  delay,
}: {
  icon: LucideIcon;
  label: string;
  x: number;
  y: number;
  delay: number;
}) {
  return (
    <motion.div
      animate={{ y: [0, -8, 0] }}
      transition={{ duration: 3, repeat: Infinity, delay }}
      className="absolute rounded-lg border border-line bg-elevated px-3 py-2 text-xs"
      style={{ left: `${x}%`, top: `${y}%` }}
    >
      <Icon className="mb-1 h-4 w-4 text-cyan" />
      {label}
    </motion.div>
  );
}
