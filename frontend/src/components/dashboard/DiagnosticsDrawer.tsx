"use client";

import React, { useEffect, useState } from "react";
import { getFullDiagnostics } from "@/services/audits/audit-service";
import { AnimatePresence, motion } from "framer-motion";
import { ChevronDown, ChevronUp, Clock, Download, Eye, FileJson, Info, Play, Server, ShieldCheck, X } from "lucide-react";

interface DiagnosticsDrawerProps {
  auditId: string;
  isOpen: boolean;
  onClose: () => void;
}

export function DiagnosticsDrawer({ auditId, isOpen, onClose }: DiagnosticsDrawerProps) {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Accordion Section States
  const [openSection, setOpenSection] = useState<string | null>("summary");

  useEffect(() => {
    if (isOpen && auditId) {
      const fetchDiagnostics = async () => {
        setLoading(true);
        setError(null);
        try {
          const diagnostics = await getFullDiagnostics(auditId);
          setData(diagnostics);
        } catch (err: any) {
          setError(err.response?.data?.detail || "Failed to load audit trail diagnostics.");
        } finally {
          setLoading(false);
        }
      };
      fetchDiagnostics();
    }
  }, [isOpen, auditId]);

  const toggleSection = (section: string) => {
    setOpenSection(openSection === section ? null : section);
  };

  const exportAsJson = () => {
    if (!data) return;
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `audit-diagnostics-trail-${auditId}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

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
            className="fixed inset-y-0 right-0 z-50 w-full max-w-2xl bg-panel border-l border-white/10 shadow-panel flex flex-col h-full"
          >
            {/* Header */}
            <div className="p-5 border-b border-line flex items-center justify-between">
              <div>
                <h3 className="font-semibold text-lg text-foreground flex items-center gap-2">
                  <Server className="h-5 w-5 text-brand" /> Regulator Audit Diagnostics
                </h3>
                <p className="text-xs text-muted">Complete transparent LLM prompts & similarity contexts</p>
              </div>
              <div className="flex items-center gap-2">
                {data && (
                  <button
                    onClick={exportAsJson}
                    className="p-1.5 rounded-lg border border-white/10 hover:bg-white/5 text-muted hover:text-foreground transition-all flex items-center gap-1.5 text-xs font-semibold"
                  >
                    <Download className="h-4 w-4" /> Export JSON
                  </button>
                )}
                <button
                  onClick={onClose}
                  className="h-8 w-8 grid place-items-center rounded-lg border border-white/10 text-muted hover:text-foreground hover:bg-white/5 transition-all"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-5 space-y-4">
              {loading && (
                <div className="flex flex-col items-center justify-center h-64 text-muted">
                  <div className="h-8 w-8 border-2 border-brand border-t-transparent rounded-full animate-spin mb-3" />
                  <p className="text-sm">Retrieving audit trace logs...</p>
                </div>
              )}

              {error && (
                <div className="text-sm text-critical bg-critical/10 border border-critical/20 p-4 rounded-lg flex items-start gap-2">
                  <Info className="h-5 w-5 shrink-0" />
                  <div>
                    <p className="font-semibold">Unable to fetch diagnostics</p>
                    <p className="text-xs opacity-80 mt-1">{error}</p>
                  </div>
                </div>
              )}

              {!loading && !error && data && (
                <div className="space-y-4">
                  {/* KPI Metrics Dashboard Grid */}
                  <div className="grid grid-cols-3 gap-3">
                    <div className="bg-white/5 p-3 rounded-lg border border-white/10 text-center">
                      <div className="text-[10px] uppercase font-bold text-muted tracking-wider">Matched Chunks</div>
                      <div className="text-xl font-bold text-foreground mt-1">
                        {data.context_chunks_snapshot?.length || 0}
                      </div>
                    </div>
                    <div className="bg-white/5 p-3 rounded-lg border border-white/10 text-center">
                      <div className="text-[10px] uppercase font-bold text-muted tracking-wider">Match Confidence</div>
                      <div className="text-xl font-bold text-cyan mt-1">
                        {data.match_confidence ? `${(data.match_confidence * 100).toFixed(0)}%` : "N/A"}
                      </div>
                    </div>
                    <div className="bg-white/5 p-3 rounded-lg border border-white/10 text-center">
                      <div className="text-[10px] uppercase font-bold text-muted tracking-wider">Blended Score</div>
                      <div className="text-xl font-bold text-brand mt-1">
                        {data.blended_confidence ? `${(data.blended_confidence * 100).toFixed(0)}%` : "N/A"}
                      </div>
                    </div>
                  </div>

                  <div className="bg-white/5 p-4 rounded-lg border border-white/10 flex items-start gap-3">
                    <ShieldCheck className="h-5 w-5 text-success mt-0.5 shrink-0" />
                    <div>
                      <h4 className="text-xs font-bold uppercase tracking-wider text-muted">Evaluation Decision</h4>
                      <p className="text-sm text-foreground mt-1 leading-relaxed">
                        {data.score_reasoning || "The system matched the document against compliance guidelines successfully."}
                      </p>
                    </div>
                  </div>

                  {/* Accordion Panels */}
                  <div className="space-y-3">
                    {/* Section 1: Final Prompt */}
                    <div className="border border-white/10 rounded-lg overflow-hidden">
                      <button
                        onClick={() => toggleSection("prompt")}
                        className="w-full bg-white/5 p-4 flex justify-between items-center text-sm font-semibold text-foreground hover:bg-white/10 transition-all"
                      >
                        <span className="flex items-center gap-2">
                          <Play className="h-4 w-4 text-cyan" /> Final Compiled System & User Prompt
                        </span>
                        {openSection === "prompt" ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                      </button>
                      {openSection === "prompt" && (
                        <div className="p-4 bg-background border-t border-white/10">
                          <pre className="text-xs font-mono text-muted overflow-x-auto whitespace-pre-wrap max-h-80 select-all p-2 rounded bg-black/40">
                            {data.final_prompt || "No prompt trace logged."}
                          </pre>
                        </div>
                      )}
                    </div>

                    {/* Section 2: LLM Raw Output */}
                    <div className="border border-white/10 rounded-lg overflow-hidden">
                      <button
                        onClick={() => toggleSection("response")}
                        className="w-full bg-white/5 p-4 flex justify-between items-center text-sm font-semibold text-foreground hover:bg-white/10 transition-all"
                      >
                        <span className="flex items-center gap-2">
                          <Eye className="h-4 w-4 text-success" /> Raw LLM JSON Response
                        </span>
                        {openSection === "response" ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                      </button>
                      {openSection === "response" && (
                        <div className="p-4 bg-background border-t border-white/10">
                          <pre className="text-xs font-mono text-success overflow-x-auto whitespace-pre-wrap max-h-80 select-all p-2 rounded bg-black/40">
                            {data.final_llm_response
                              ? (() => {
                                  try {
                                    return JSON.stringify(JSON.parse(data.final_llm_response), null, 2);
                                  } catch (_) {
                                    return data.final_llm_response;
                                  }
                                })()
                              : "No LLM response trace logged."}
                          </pre>
                        </div>
                      )}
                    </div>

                    {/* Section 3: Context Chunks */}
                    <div className="border border-white/10 rounded-lg overflow-hidden">
                      <button
                        onClick={() => toggleSection("chunks")}
                        className="w-full bg-white/5 p-4 flex justify-between items-center text-sm font-semibold text-foreground hover:bg-white/10 transition-all"
                      >
                        <span className="flex items-center gap-2">
                          <FileJson className="h-4 w-4 text-brand" /> Retrieved Reference Document Chunks
                        </span>
                        {openSection === "chunks" ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                      </button>
                      {openSection === "chunks" && (
                        <div className="p-4 bg-background border-t border-white/10 space-y-3">
                          {data.context_chunks_snapshot?.map((chunk: any, index: number) => (
                            <div key={index} className="border border-white/5 p-3 rounded bg-white/5 space-y-1">
                              <div className="flex justify-between items-center text-[10px] font-bold text-brand uppercase tracking-wider">
                                <span>Chunk #{index + 1}</span>
                                <span className="font-mono text-muted">ID: {chunk.chunk_id}</span>
                              </div>
                              <p className="text-xs text-foreground/80 leading-relaxed font-sans mt-1">
                                {chunk.text_preview}
                              </p>
                            </div>
                          )) || <p className="text-xs text-muted">No chunk snapshot compiled.</p>}
                        </div>
                      )}
                    </div>

                    {/* Section 4: Retry / Attempt Log */}
                    <div className="border border-white/10 rounded-lg overflow-hidden">
                      <button
                        onClick={() => toggleSection("retries")}
                        className="w-full bg-white/5 p-4 flex justify-between items-center text-sm font-semibold text-foreground hover:bg-white/10 transition-all"
                      >
                        <span className="flex items-center gap-2">
                          <Clock className="h-4 w-4 text-warning" /> Execution Retry Logs & Failures
                        </span>
                        {openSection === "retries" ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                      </button>
                      {openSection === "retries" && (
                        <div className="p-4 bg-background border-t border-white/10 space-y-2">
                          {data.retry_attempts?.map((attempt: any, index: number) => (
                            <div key={index} className="border border-white/5 p-3 rounded bg-white/5 text-xs space-y-2">
                              <div className="flex justify-between items-center">
                                <span className="font-semibold text-foreground">Attempt #{attempt.attempt}</span>
                                <span className={attempt.error ? "text-critical font-semibold" : "text-success font-semibold"}>
                                  {attempt.error ? "Failed" : "Success"}
                                </span>
                              </div>
                              <div className="grid grid-cols-2 gap-2 text-muted text-[10px] uppercase font-bold tracking-wider">
                                <div>Rule Candidates: {attempt.rule_candidates}</div>
                                <div>Max Tokens: {attempt.max_tokens}</div>
                              </div>
                              {attempt.error && (
                                <div className="text-critical bg-critical/5 p-2 rounded border border-critical/10 font-mono text-[10px]">
                                  {attempt.error}
                                </div>
                              )}
                            </div>
                          )) || <p className="text-xs text-muted">No retry log recorded.</p>}
                        </div>
                      )}
                    </div>
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
