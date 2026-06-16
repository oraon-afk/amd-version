"use client";

import React, { useEffect, useState } from "react";
import { getReviewHistory } from "@/services/audits/audit-service";
import { Finding } from "@/types/api";
import { Calendar, ChevronRight, Clock, FileText, User, X } from "lucide-react";
import { AnimatePresence, motion } from "framer-motion";

interface ReviewHistoryDrawerProps {
  auditId: string;
  isOpen: boolean;
  onClose: () => void;
}

export function ReviewHistoryDrawer({ auditId, isOpen, onClose }: ReviewHistoryDrawerProps) {
  const [history, setHistory] = useState<Finding[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen && auditId) {
      const fetchHistory = async () => {
        setLoading(true);
        setError(null);
        try {
          const data = await getReviewHistory(auditId);
          setHistory(data);
        } catch (err: any) {
          setError("Failed to load review history.");
        } finally {
          setLoading(false);
        }
      };
      fetchHistory();
    }
  }, [isOpen, auditId]);

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
              <div>
                <h3 className="font-semibold text-lg text-foreground">Review History & Audit Trail</h3>
                <p className="text-xs text-muted">Immutable log of compliance decisions</p>
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
                <div className="flex flex-col items-center justify-center h-48 text-muted">
                  <div className="h-6 w-6 border-2 border-brand border-t-transparent rounded-full animate-spin mb-2" />
                  <p className="text-sm">Loading review history...</p>
                </div>
              )}

              {error && (
                <div className="text-sm text-critical bg-critical/10 border border-critical/20 p-4 rounded-lg">
                  {error}
                </div>
              )}

              {!loading && !error && history.length === 0 && (
                <div className="text-center text-muted h-48 flex flex-col justify-center">
                  <Clock className="h-8 w-8 mx-auto mb-2 opacity-50" />
                  <p className="text-sm">No review history available.</p>
                  <p className="text-xs mt-1">Accept, reject, or modify high-risk findings to log history.</p>
                </div>
              )}

              {!loading && !error && history.length > 0 && (
                <div className="relative border-l border-line pl-6 ml-3 space-y-8">
                  {history.map((item) => {
                    const reviewedAtStr = item.reviewed_at
                      ? new Date(item.reviewed_at).toLocaleString()
                      : "Unknown date";
                    
                    const isModified = item.review_status === "modified";
                    const isRejected = item.review_status === "rejected";
                    const isAccepted = item.review_status === "accepted";

                    let statusBadge = "bg-success/10 text-success border-success/30";
                    if (isRejected) statusBadge = "bg-critical/10 text-critical border-critical/30";
                    if (isModified) statusBadge = "bg-brand/10 text-brand border-brand/30";

                    return (
                      <div key={item.id} className="relative">
                        {/* Timeline Node Icon */}
                        <div className="absolute -left-10 top-0.5 h-7 w-7 rounded-full border border-line bg-panel grid place-items-center text-brand">
                          <FileText className="h-3.5 w-3.5" />
                        </div>

                        {/* Timeline Card */}
                        <div className="glass-panel border-line p-4 rounded-lg space-y-3">
                          <div className="flex justify-between items-start">
                            <div>
                              <span className={`text-[10px] font-semibold uppercase tracking-wider border px-2 py-0.5 rounded ${statusBadge}`}>
                                {item.review_status}
                              </span>
                              <h4 className="font-semibold text-sm text-foreground mt-1.5 uppercase tracking-wide">
                                {item.finding_type.replace(/_/g, " ")}
                              </h4>
                            </div>
                            <span className="text-[10px] text-muted font-mono">{reviewedAtStr}</span>
                          </div>

                          <div className="flex items-center gap-4 text-xs text-muted">
                            <span className="flex items-center gap-1">
                              <User className="h-3.5 w-3.5" /> Admin
                            </span>
                            <span className="flex items-center gap-1 font-mono text-[10px]">
                              Rule: {item.violated_rule.substring(0, 20)}...
                            </span>
                          </div>

                          {item.review_comment && (
                            <div className="bg-white/5 p-3 rounded border border-white/5 text-sm text-foreground/80 font-serif italic">
                              "{item.review_comment}"
                            </div>
                          )}

                          {isModified && item.original_finding_snapshot && (
                            <div className="bg-background/80 p-3 rounded border border-white/5 space-y-2 text-xs">
                              <div className="font-semibold text-[10px] uppercase tracking-wider text-muted mb-1">
                                Field Modifications Diff
                              </div>
                              
                              {/* Risk diff */}
                              {item.original_finding_snapshot.risk_level !== item.risk_level && (
                                <div className="flex items-center gap-2">
                                  <span className="text-muted w-16">Risk:</span>
                                  <span className="text-critical/80 line-through">{item.original_finding_snapshot.risk_level}</span>
                                  <ChevronRight className="h-3 w-3 text-muted" />
                                  <span className="text-success font-semibold">{item.risk_level}</span>
                                </div>
                              )}

                              {/* Severity diff */}
                              {item.original_finding_snapshot.severity !== item.severity && (
                                <div className="flex items-center gap-2">
                                  <span className="text-muted w-16">Severity:</span>
                                  <span className="text-critical/80 line-through">{item.original_finding_snapshot.severity}</span>
                                  <ChevronRight className="h-3 w-3 text-muted" />
                                  <span className="text-success font-semibold">{item.severity}</span>
                                </div>
                              )}

                              {/* Explanation diff */}
                              {item.original_finding_snapshot.explanation !== item.explanation && (
                                <div className="space-y-1">
                                  <div className="text-muted">Explanation changed:</div>
                                  <div className="text-critical/80 line-through bg-critical/5 p-1 rounded font-mono text-[10px]">
                                    {item.original_finding_snapshot.explanation.substring(0, 100)}...
                                  </div>
                                  <div className="text-success bg-success/5 p-1 rounded font-mono text-[10px]">
                                    {item.explanation.substring(0, 100)}...
                                  </div>
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
