"use client";

import React, { useEffect, useState } from "react";
import { getFindingExplanation } from "@/services/audits/audit-service";
import { Brain, Calendar, ChevronRight, FileText, Sparkles, X, Target } from "lucide-react";
import { AnimatePresence, motion } from "framer-motion";
import { Badge } from "@/components/ui/badge";

interface EvidenceItem {
  text: string;
  page?: number | null;
  section?: string | null;
}

interface FindingExplanationData {
  finding_id: string;
  explanation_text: string;
  evidence_list: EvidenceItem[];
  confidence_score: number;
}

interface FindingExplanationDrawerProps {
  findingId: string | null;
  isOpen: boolean;
  onClose: () => void;
}

export function FindingExplanationDrawer({ findingId, isOpen, onClose }: FindingExplanationDrawerProps) {
  const [data, setData] = useState<FindingExplanationData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen && findingId) {
      const fetchExplanation = async () => {
        setLoading(true);
        setError(null);
        setData(null);
        try {
          const res = await getFindingExplanation(findingId);
          setData(res);
        } catch (err: any) {
          setError("Failed to generate or fetch AI explanation.");
        } finally {
          setLoading(false);
        }
      };
      fetchExplanation();
    }
  }, [isOpen, findingId]);

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 0.5 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 z-40 bg-black"
          />

          {/* Drawer Panel */}
          <motion.div
            initial={{ x: "100%" }}
            animate={{ x: 0 }}
            exit={{ x: "100%" }}
            transition={{ type: "spring", damping: 25, stiffness: 200 }}
            className="fixed inset-y-0 right-0 z-50 w-full max-w-lg bg-panel border-l border-white/10 shadow-panel flex flex-col h-full"
          >
            {/* Header */}
            <div className="p-5 border-b border-line flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="p-2 rounded-lg bg-brand/10 text-brand">
                  <Brain className="h-5 w-5 animate-pulse" />
                </div>
                <div>
                  <h3 className="font-semibold text-lg text-foreground flex items-center gap-1.5">
                    AI Finding Explanation
                  </h3>
                  <p className="text-xs text-muted">Deep reasoning on rule violation</p>
                </div>
              </div>
              <button
                onClick={onClose}
                className="h-8 w-8 grid place-items-center rounded-lg border border-white/10 text-muted hover:text-foreground hover:bg-white/5 transition-all"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-5 space-y-6">
              {loading && (
                <div className="flex flex-col items-center justify-center h-64 text-muted">
                  <div className="relative mb-4">
                    <div className="h-10 w-10 border-4 border-brand border-t-transparent rounded-full animate-spin" />
                    <Sparkles className="h-4 w-4 text-warning absolute top-3 left-3 animate-ping" />
                  </div>
                  <p className="text-sm font-medium">Synthesizing compliance explanation...</p>
                  <p className="text-xs text-muted/80 mt-1">Analyzing evidence and rule mismatches</p>
                </div>
              )}

              {error && (
                <div className="text-sm text-critical bg-critical/10 border border-critical/20 p-4 rounded-lg">
                  {error}
                </div>
              )}

              {!loading && !error && data && (
                <div className="space-y-6">
                  {/* Confidence Panel */}
                  <div className="rounded-lg border border-line bg-white/5 p-4 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Target className="h-5 w-5 text-cyan" />
                      <div>
                        <div className="text-xs font-semibold uppercase text-muted">AI Explanation Confidence</div>
                        <div className="text-sm font-medium text-foreground">Based on historical audit data</div>
                      </div>
                    </div>
                    <Badge variant="cyan" className="text-sm font-mono px-2.5 py-1">
                      {Math.round(data.confidence_score * 100)}%
                    </Badge>
                  </div>

                  {/* Explanation Text */}
                  <div className="space-y-2">
                    <div className="text-xs font-semibold uppercase text-muted tracking-wider">Reason for flagging</div>
                    <div className="bg-white/5 border border-line p-4 rounded-lg text-sm leading-6 text-foreground/90 font-sans whitespace-pre-wrap">
                      {data.explanation_text}
                    </div>
                  </div>

                  {/* Evidence List */}
                  <div className="space-y-3">
                    <div className="text-xs font-semibold uppercase text-muted tracking-wider">Citations & Extracted Evidence</div>
                    {data.evidence_list.length === 0 ? (
                      <p className="text-xs text-muted">No specific citations matched for this explanation.</p>
                    ) : (
                      <div className="space-y-3">
                        {data.evidence_list.map((item, idx) => (
                          <div key={idx} className="glass-panel border-line p-4 rounded-lg space-y-2.5">
                            <div className="flex flex-wrap items-center gap-2">
                              <span className="text-xs font-mono font-bold bg-white/5 text-muted px-1.5 py-0.5 rounded border border-white/5">
                                #{idx + 1}
                              </span>
                              {item.section && (
                                <Badge variant="muted" className="text-[10px]">
                                  Section: {item.section}
                                </Badge>
                              )}
                              {item.page !== undefined && item.page !== null && (
                                <Badge variant="muted" className="text-[10px]">
                                  Page: {item.page}
                                </Badge>
                              )}
                            </div>
                            <blockquote className="border-l-2 border-brand/50 pl-3 py-0.5 text-xs italic text-muted leading-5">
                              "{item.text}"
                            </blockquote>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
