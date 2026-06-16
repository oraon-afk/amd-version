"use client";

import React, { useState } from "react";
import { Finding } from "@/types/api";
import { reviewFinding } from "@/services/audits/audit-service";
import { AlertCircle, Check, CornerDownRight, Edit3, X } from "lucide-react";

interface FindingsReviewPanelProps {
  auditId: string;
  findings: Finding[];
  onReviewComplete: () => void;
}

export function FindingsReviewPanel({ auditId, findings, onReviewComplete }: FindingsReviewPanelProps) {
  const pendingFindings = findings.filter(
    (f) => f.needs_review && f.review_status === "pending"
  );

  const [activeFindingId, setActiveFindingId] = useState<string | null>(null);
  const [actionType, setActionType] = useState<"accept" | "reject" | "modify" | null>(null);
  const [comment, setComment] = useState("");
  
  // Fields for modification
  const [modifiedFields, setModifiedFields] = useState<{
    risk_level: string;
    severity: string;
    explanation: string;
    recommendation: string;
  }>({
    risk_level: "MEDIUM",
    severity: "MEDIUM",
    explanation: "",
    recommendation: "",
  });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const startReview = (finding: Finding, type: "accept" | "reject" | "modify") => {
    setActiveFindingId(finding.id);
    setActionType(type);
    setComment("");
    setModifiedFields({
      risk_level: finding.risk_level,
      severity: finding.severity,
      explanation: finding.explanation,
      recommendation: finding.recommendation,
    });
    setError(null);
  };

  const cancelReview = () => {
    setActiveFindingId(null);
    setActionType(null);
    setComment("");
  };

  const submitReview = async () => {
    if (!activeFindingId || !actionType) return;
    
    if ((actionType === "reject" || actionType === "modify") && !comment.trim()) {
      setError("A comment/justification is required to reject or modify this finding.");
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const payload: any = {
        action: actionType,
        comment: comment,
      };

      if (actionType === "modify") {
        payload.modified_fields = {
          risk_level: modifiedFields.risk_level,
          severity: modifiedFields.severity,
          explanation: modifiedFields.explanation,
          recommendation: modifiedFields.recommendation,
        };
      }

      await reviewFinding(activeFindingId, payload);
      cancelReview();
      onReviewComplete();
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to submit review.");
    } finally {
      setLoading(false);
    }
  };

  if (findings.length === 0) {
    return (
      <div className="glass-panel rounded-lg p-8 text-center text-muted">
        <p>No findings recorded for this report.</p>
      </div>
    );
  }

  if (pendingFindings.length === 0) {
    return (
      <div className="glass-panel rounded-lg p-8 text-center border-success/20 bg-success/5 text-success">
        <div className="flex justify-center mb-2">
          <Check className="h-8 w-8 text-success" />
        </div>
        <p className="font-semibold">All findings reviewed</p>
        <p className="text-sm text-muted mt-1">This report is ready to be published.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2 text-warning">
        <AlertCircle className="h-5 w-5" />
        <h3 className="font-semibold text-foreground">
          {pendingFindings.length} Finding{pendingFindings.length > 1 ? "s" : ""} Require Compliance Review
        </h3>
      </div>

      <div className="space-y-4">
        {pendingFindings.map((finding) => {
          const isReviewing = activeFindingId === finding.id;

          return (
            <div
              key={finding.id}
              className="glass-panel border-warning/20 bg-warning/5 rounded-lg p-5 transition-all"
            >
              <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-4">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-semibold uppercase tracking-wider bg-critical/20 text-critical border border-critical/30 px-2 py-0.5 rounded">
                      {finding.risk_level} Risk
                    </span>
                    <span className="text-muted text-xs">Violated Rule:</span>
                    <span className="text-foreground text-xs font-mono font-semibold">
                      {finding.violated_rule.length > 50
                        ? `${finding.violated_rule.substring(0, 50)}...`
                        : finding.violated_rule}
                    </span>
                  </div>
                  <h4 className="text-lg font-semibold mt-2 text-foreground">
                    {finding.finding_type.replace(/_/g, " ").toUpperCase()}
                  </h4>
                </div>

                {!isReviewing && (
                  <div className="flex items-center gap-2 self-end md:self-auto">
                    <button
                      onClick={() => startReview(finding, "accept")}
                      className="px-3 py-1.5 text-xs font-semibold rounded bg-success/10 text-success border border-success/30 hover:bg-success/20 transition-all flex items-center gap-1"
                    >
                      <Check className="h-3 w-3" /> Accept
                    </button>
                    <button
                      onClick={() => startReview(finding, "modify")}
                      className="px-3 py-1.5 text-xs font-semibold rounded bg-brand/10 text-brand border border-brand/30 hover:bg-brand/20 transition-all flex items-center gap-1"
                    >
                      <Edit3 className="h-3 w-3" /> Modify
                    </button>
                    <button
                      onClick={() => startReview(finding, "reject")}
                      className="px-3 py-1.5 text-xs font-semibold rounded bg-critical/10 text-critical border border-critical/30 hover:bg-critical/20 transition-all flex items-center gap-1"
                    >
                      <X className="h-3 w-3" /> Reject
                    </button>
                  </div>
                )}
              </div>

              <div className="text-sm space-y-2 mb-4 text-foreground/80">
                <p>
                  <strong className="text-muted block text-xs uppercase tracking-wider mb-1">
                    Explanation
                  </strong>
                  {finding.explanation}
                </p>
                <p>
                  <strong className="text-muted block text-xs uppercase tracking-wider mb-1">
                    Recommendation
                  </strong>
                  {finding.recommendation}
                </p>
              </div>

              {isReviewing && (
                <div className="mt-4 border-t border-line pt-4 space-y-4">
                  <h5 className="font-semibold text-sm text-foreground flex items-center gap-1">
                    <CornerDownRight className="h-4 w-4 text-brand" /> 
                    Reviewing Finding (Action: <span className="uppercase text-brand">{actionType}</span>)
                  </h5>

                  {actionType === "modify" && (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 bg-white/5 p-4 rounded-lg border border-white/10">
                      <div>
                        <label className="block text-xs text-muted mb-1 uppercase tracking-wider">Risk Level</label>
                        <select
                          value={modifiedFields.risk_level}
                          onChange={(e) => setModifiedFields({ ...modifiedFields, risk_level: e.target.value })}
                          className="w-full bg-background border border-white/10 text-foreground text-sm rounded p-2 focus:border-brand outline-none"
                        >
                          <option value="LOW">Low</option>
                          <option value="MEDIUM">Medium</option>
                          <option value="HIGH">High</option>
                          <option value="CRITICAL">Critical</option>
                        </select>
                      </div>
                      <div>
                        <label className="block text-xs text-muted mb-1 uppercase tracking-wider">Severity</label>
                        <select
                          value={modifiedFields.severity}
                          onChange={(e) => setModifiedFields({ ...modifiedFields, severity: e.target.value })}
                          className="w-full bg-background border border-white/10 text-foreground text-sm rounded p-2 focus:border-brand outline-none"
                        >
                          <option value="LOW">Low</option>
                          <option value="MEDIUM">Medium</option>
                          <option value="HIGH">High</option>
                          <option value="CRITICAL">Critical</option>
                        </select>
                      </div>
                      <div className="md:col-span-2">
                        <label className="block text-xs text-muted mb-1 uppercase tracking-wider">Explanation</label>
                        <textarea
                          rows={3}
                          value={modifiedFields.explanation}
                          onChange={(e) => setModifiedFields({ ...modifiedFields, explanation: e.target.value })}
                          className="w-full bg-background border border-white/10 text-foreground text-sm rounded p-2 focus:border-brand outline-none"
                        />
                      </div>
                      <div className="md:col-span-2">
                        <label className="block text-xs text-muted mb-1 uppercase tracking-wider">Recommendation</label>
                        <textarea
                          rows={3}
                          value={modifiedFields.recommendation}
                          onChange={(e) => setModifiedFields({ ...modifiedFields, recommendation: e.target.value })}
                          className="w-full bg-background border border-white/10 text-foreground text-sm rounded p-2 focus:border-brand outline-none"
                        />
                      </div>
                    </div>
                  )}

                  <div>
                    <label className="block text-xs text-muted mb-1 uppercase tracking-wider">
                      Review Comment / Justification {(actionType === "reject" || actionType === "modify") && "*"}
                    </label>
                    <textarea
                      rows={2}
                      placeholder={
                        actionType === "accept"
                          ? "Add review notes (optional)..."
                          : "Provide mandatory reasoning for this action..."
                      }
                      value={comment}
                      onChange={(e) => setComment(e.target.value)}
                      className="w-full bg-background border border-white/10 text-foreground text-sm rounded p-2 focus:border-brand outline-none"
                    />
                  </div>

                  {error && (
                    <div className="text-xs text-critical bg-critical/10 border border-critical/20 p-2 rounded">
                      {error}
                    </div>
                  )}

                  <div className="flex items-center gap-2 justify-end">
                    <button
                      onClick={cancelReview}
                      disabled={loading}
                      className="px-3 py-1.5 text-xs font-semibold bg-white/5 border border-white/10 hover:bg-white/10 text-muted hover:text-foreground rounded transition-all"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={submitReview}
                      disabled={loading}
                      className="px-3 py-1.5 text-xs font-semibold bg-brand hover:bg-brand/90 text-white rounded transition-all shadow-[0_0_12px_rgba(124,77,255,0.3)] disabled:opacity-50"
                    >
                      {loading ? "Submitting..." : "Submit Review"}
                    </button>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
