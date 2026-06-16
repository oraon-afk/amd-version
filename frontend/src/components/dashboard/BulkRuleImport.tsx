"use client";

import React, { useRef, useState } from "react";
import { apiClient } from "@/services/api/client";
import { AlertCircle, CheckCircle, FileSpreadsheet, Loader2, UploadCloud } from "lucide-react";

interface BulkRuleImportProps {
  onImportComplete: () => void;
}

export function BulkRuleImport({ onImportComplete }: BulkRuleImportProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState<{ current: number; total: number } | null>(null);
  const [logs, setLogs] = useState<{ type: "success" | "error"; message: string }[]>([]);
  const [error, setError] = useState<string | null>(null);

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setLoading(true);
    setLogs([]);
    setError(null);
    setProgress(null);

    try {
      const text = await file.text();
      let rules: any[] = [];

      if (file.name.endsWith(".json")) {
        try {
          rules = JSON.parse(text);
          if (!Array.isArray(rules)) {
            rules = [rules];
          }
        } catch (err) {
          throw new Error("Invalid JSON file format. Make sure it's valid JSON.");
        }
      } else if (file.name.endsWith(".csv")) {
        // Basic CSV Parsing
        const lines = text.split(/\r?\n/);
        const headers = lines[0].split(",").map((h) => h.trim().replace(/^"|"$/g, ""));
        
        for (let i = 1; i < lines.length; i++) {
          const line = lines[i].trim();
          if (!line) continue;
          
          // Match commas except inside double quotes
          const matches = line.match(/(".*?"|[^",\s]+)(?=\s*,|\s*$)/g) || line.split(",");
          const values = matches.map((v) => v.trim().replace(/^"|"$/g, ""));
          
          const rule: any = {};
          headers.forEach((header, idx) => {
            if (values[idx] !== undefined) {
              rule[header] = values[idx];
            }
          });

          // Check minimum fields
          if (rule.category && rule.title && rule.rule_text) {
            rules.push(rule);
          }
        }
      } else {
        throw new Error("Unsupported file type. Please upload a .json or .csv file.");
      }

      if (rules.length === 0) {
        throw new Error("No valid rules found in the file. Ensure you have 'category', 'title', and 'rule_text' columns.");
      }

      setProgress({ current: 0, total: rules.length });

      // Sequentially process each rule
      for (let i = 0; i < rules.length; i++) {
        const rule = rules[i];
        try {
          await apiClient.post("/admin/compliance-rules", {
            category: rule.category || "General",
            title: rule.title || "Untitled Rule",
            description: rule.description || "",
            rule_text: rule.rule_text || "",
            reference: rule.reference || "",
            version: rule.version || "v1",
            custom_attributes: rule.custom_attributes ? (typeof rule.custom_attributes === 'string' ? JSON.parse(rule.custom_attributes) : rule.custom_attributes) : null,
          });

          setLogs((prev) => [
            ...prev,
            { type: "success", message: `Successfully imported: "${rule.title}"` },
          ]);
        } catch (err: any) {
          const errMsg = err.response?.data?.detail || err.message || "Failed to create rule.";
          setLogs((prev) => [
            ...prev,
            { type: "error", message: `Failed to import: "${rule.title}" - ${errMsg}` },
          ]);
        }
        setProgress((prev) => prev ? { ...prev, current: i + 1 } : null);
      }

      onImportComplete();
    } catch (err: any) {
      setError(err.message || "An error occurred during file parsing.");
    } finally {
      setLoading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  return (
    <div className="glass-panel border-line bg-panel p-6 rounded-lg space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h4 className="font-semibold text-foreground flex items-center gap-2">
            <FileSpreadsheet className="h-5 w-5 text-brand" /> Bulk Rule Import
          </h4>
          <p className="text-xs text-muted">Import multiple compliance rules via JSON or CSV file</p>
        </div>
      </div>

      <div
        onClick={() => !loading && fileInputRef.current?.click()}
        className={`border-2 border-dashed border-line rounded-lg p-6 text-center transition-all ${
          loading ? "opacity-60 cursor-not-allowed" : "cursor-pointer hover:border-brand/40 hover:bg-white/5"
        }`}
      >
        <input
          type="file"
          ref={fileInputRef}
          onChange={handleFileChange}
          accept=".csv,.json"
          className="hidden"
          disabled={loading}
        />
        {loading ? (
          <div className="flex flex-col items-center justify-center space-y-2 text-muted">
            <Loader2 className="h-8 w-8 animate-spin text-brand" />
            <p className="text-sm font-semibold">Importing rules...</p>
            {progress && (
              <p className="text-xs">
                Processed {progress.current} of {progress.total} rules (
                {Math.round((progress.current / progress.total) * 100)}%)
              </p>
            )}
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center space-y-2 text-muted">
            <UploadCloud className="h-10 w-10 text-brand" />
            <p className="text-sm font-semibold text-foreground">Click to upload file</p>
            <p className="text-xs">Supports JSON array or CSV containing title, category, rule_text</p>
          </div>
        )}
      </div>

      {error && (
        <div className="text-xs text-critical bg-critical/10 border border-critical/20 p-3 rounded-lg flex items-center gap-2">
          <AlertCircle className="h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {logs.length > 0 && (
        <div className="bg-background/50 border border-white/10 rounded-lg p-4 max-h-48 overflow-y-auto space-y-1.5 font-mono text-[11px]">
          <div className="flex justify-between items-center text-xs font-bold text-muted border-b border-white/10 pb-1.5 mb-2 font-sans">
            <span>Import Summary Log</span>
            <span className="flex items-center gap-3">
              <span className="text-success">Success: {logs.filter((l) => l.type === "success").length}</span>
              <span className="text-critical">Errors: {logs.filter((l) => l.type === "error").length}</span>
            </span>
          </div>
          {logs.map((log, idx) => (
            <div key={idx} className={log.type === "success" ? "text-success/90" : "text-critical/95"}>
              {log.type === "success" ? (
                <CheckCircle className="h-3 w-3 inline mr-1.5" />
              ) : (
                <AlertCircle className="h-3 w-3 inline mr-1.5" />
              )}
              {log.message}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
