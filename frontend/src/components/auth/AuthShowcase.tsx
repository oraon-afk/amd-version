"use client";

import { motion } from "framer-motion";
import { FileCheck2, Radar, ShieldCheck, Sparkles, type LucideIcon } from "lucide-react";

export function AuthShowcase({ mode }: { mode: "login" | "register" }) {
  return (
    <section className="relative hidden overflow-hidden border-r border-line p-10 lg:block">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_45%_28%,rgba(124,58,237,0.26),transparent_22rem)]" />
      <div className="relative z-10 flex h-full flex-col justify-between">
        <div>
          <div className="mb-8 flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-gradient-to-br from-violet to-cyan shadow-glow">
              <ShieldCheck className="h-5 w-5 text-white" />
            </div>
            <div>
              <div className="font-semibold">Audit AI</div>
              <div className="text-xs text-muted">Evidence-ready compliance assistant</div>
            </div>
          </div>
          <h2 className="max-w-md text-4xl font-semibold leading-tight">
            {mode === "login" ? "Welcome back to your audit command center." : "Join the most advanced compliance workspace."}
          </h2>
          <p className="mt-4 max-w-md text-sm leading-6 text-muted">
            Validate documents, trace citations, surface violations, and generate executive-ready reports with grounded AI.
          </p>
        </div>
        <motion.div
          initial={{ opacity: 0, scale: 0.94 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.15 }}
          className="glass-panel neon-border relative mx-auto aspect-square w-[360px] rounded-[2rem] p-8"
        >
          <div className="absolute inset-8 rounded-[1.5rem] border border-violet/20 bg-violet/10" />
          <div className="absolute left-1/2 top-1/2 flex h-28 w-28 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-3xl bg-gradient-to-br from-violet to-cyan shadow-glow">
            <ShieldCheck className="h-12 w-12 text-white" />
          </div>
          <FloatingLabel icon={FileCheck2} label="Validation" x={20} y={28} delay={0.2} />
          <FloatingLabel icon={Radar} label="Rules" x={66} y={18} delay={0.66} />
          <FloatingLabel icon={Sparkles} label="Reports" x={68} y={68} delay={0.68} />
          <FloatingLabel icon={ShieldCheck} label="Controls" x={16} y={72} delay={0.16} />
        </motion.div>
        <div className="grid grid-cols-2 gap-3 text-sm">
          <div className="rounded-xl border border-line bg-white/5 p-3 text-muted">Document upload</div>
          <div className="rounded-xl border border-line bg-white/5 p-3 text-muted">Rule retrieval</div>
          <div className="rounded-xl border border-line bg-white/5 p-3 text-muted">LLM analysis</div>
          <div className="rounded-xl border border-line bg-white/5 p-3 text-muted">Report export</div>
        </div>
      </div>
    </section>
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
      className="absolute rounded-xl border border-line bg-white/8 px-3 py-2 text-xs"
      style={{ left: `${x}%`, top: `${y}%` }}
    >
      <Icon className="mb-1 h-4 w-4 text-cyan" />
      {label}
    </motion.div>
  );
}
