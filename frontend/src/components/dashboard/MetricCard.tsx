"use client";

import { motion } from "framer-motion";
import { type LucideIcon } from "lucide-react";
import { useCallback, useRef, useState } from "react";
import { CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

const toneClasses = {
  cyan: "border-cyan/35 bg-cyan/10 text-cyan",
  low: "border-cyan/35 bg-cyan/10 text-cyan",
  medium: "border-riskMedium/35 bg-riskMedium/10 text-riskMedium",
  high: "border-riskHigh/35 bg-riskHigh/10 text-riskHigh",
  muted: "border-line bg-white/6 text-muted",
};

export function MetricCard({
  icon: Icon,
  label,
  value,
  detail,
  tone = "cyan",
}: {
  icon: LucideIcon;
  label: string;
  value: string | number;
  detail?: string;
  tone?: keyof typeof toneClasses;
}) {
  const cardRef = useRef<HTMLDivElement>(null);
  const [tilt, setTilt] = useState({ rotateX: 0, rotateY: 0 });

  const handleMouseMove = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    const el = cardRef.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    const centerX = rect.width / 2;
    const centerY = rect.height / 2;
    const rotateY = ((x - centerX) / centerX) * 6;
    const rotateX = ((centerY - y) / centerY) * 6;
    setTilt({ rotateX, rotateY });
  }, []);

  const handleMouseLeave = useCallback(() => {
    setTilt({ rotateX: 0, rotateY: 0 });
  }, []);

  return (
    <motion.div
      ref={cardRef}
      initial={{ scale: 0.92, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      transition={{ type: "spring", stiffness: 200, damping: 20 }}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      style={{
        rotateX: tilt.rotateX,
        rotateY: tilt.rotateY,
        transformPerspective: 1000,
        transformStyle: "preserve-3d",
        transition: "transform 0.15s ease-out",
      }}
      className="glass-panel overflow-hidden rounded-lg transition-shadow duration-300 hover:shadow-[0_20px_40px_rgba(124,77,255,0.12)]"
    >
      <CardContent className="p-4">
        <div className="flex items-start justify-between gap-3">
          <div>
            <div className="text-xs font-semibold uppercase tracking-[0.16em] text-muted">{label}</div>
            <div className="mt-2 text-3xl font-semibold tracking-tight">{value}</div>
          </div>
          <div className={cn("grid h-10 w-10 place-items-center rounded-lg border", toneClasses[tone])}>
            <Icon className="h-5 w-5" />
          </div>
        </div>
        {detail && <p className="mt-3 text-sm text-muted">{detail}</p>}
      </CardContent>
    </motion.div>
  );
}
