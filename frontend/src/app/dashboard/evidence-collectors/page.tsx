"use client";

import React, { useEffect, useState } from "react";
import { apiClient } from "@/services/api/client";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useToast } from "@/components/ui/toast";
import {
  Activity,
  Calendar,
  Database,
  FileCode,
  Globe,
  List,
  Loader2,
  Play,
  Plus,
  RefreshCw,
  Search,
  Server,
  Trash2,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface EvidenceCollector {
  id: string;
  user_id: string;
  name: string;
  collector_type: "http" | "sql" | "script" | string;
  config: Record<string, any>;
  schedule: string | null;
  target_domain: string | null;
  document_id: string | null;
  is_active: boolean;
  last_run_at: string | null;
  last_run_status: string | null;
  created_at: string;
}

interface EvidenceLog {
  id: string;
  evidence_text: string;
  citation_label: string;
  confidence_score: number;
  collected_at: string;
  source_type: string;
  raw_payload?: Record<string, any>;
}

export default function EvidenceCollectorsPage() {
  const { toast } = useToast();
  const [collectors, setCollectors] = useState<EvidenceCollector[]>([]);
  const [loading, setLoading] = useState(false);
  const [activeCollector, setActiveCollector] = useState<EvidenceCollector | null>(null);
  const [evidenceLogs, setEvidenceLogs] = useState<EvidenceLog[]>([]);
  const [loadingLogs, setLoadingLogs] = useState(false);

  // Form Fields
  const [showAddForm, setShowAddForm] = useState(false);
  const [name, setName] = useState("");
  const [type, setType] = useState<"http" | "sql" | "script">("http");
  const [schedule, setSchedule] = useState("0 */12 * * *");
  const [targetDomain, setTargetDomain] = useState("General");
  const [httpUrl, setHttpUrl] = useState("");
  const [httpMethod, setHttpMethod] = useState("GET");
  const [httpHeaders, setHttpHeaders] = useState("");
  const [sqlDbUrl, setSqlDbUrl] = useState("");
  const [sqlQuery, setSqlQuery] = useState("");
  const [scriptPath, setScriptPath] = useState("");
  const [mappingEvidenceText, setMappingEvidenceText] = useState("$.evidence_text");
  const [mappingCitationLabel, setMappingCitationLabel] = useState("$.citation_label");

  useEffect(() => {
    fetchCollectors();
  }, []);

  const fetchCollectors = async () => {
    setLoading(true);
    try {
      const { data } = await apiClient.get<EvidenceCollector[]>("/evidence-collectors");
      setCollectors(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateCollector = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;

    let config: Record<string, any> = {};
    if (type === "http") {
      let headersObj = {};
      try {
        if (httpHeaders.trim()) {
          headersObj = JSON.parse(httpHeaders);
        }
      } catch (_) {
        toast({ title: "Invalid Headers JSON", description: "Make sure headers are formatted as valid JSON.", variant: "error" });
        return;
      }
      config = {
        url: httpUrl,
        method: httpMethod,
        headers: headersObj,
        response_mapping: {
          evidence_text: mappingEvidenceText,
          citation_label: mappingCitationLabel,
        },
      };
    } else if (type === "sql") {
      config = {
        db_url: sqlDbUrl,
        query: sqlQuery,
        response_mapping: {
          evidence_text: mappingEvidenceText,
          citation_label: mappingCitationLabel,
        },
      };
    } else if (type === "script") {
      config = {
        script_path: scriptPath,
        response_mapping: {
          evidence_text: mappingEvidenceText,
          citation_label: mappingCitationLabel,
        },
      };
    }

    try {
      await apiClient.post("/evidence-collectors", {
        name,
        collector_type: type,
        config,
        schedule: schedule || null,
        target_domain: targetDomain || null,
      });
      toast({ title: "Collector Created", description: "Your evidence collector is set up and active.", variant: "success" });
      setShowAddForm(false);
      setName("");
      setHttpUrl("");
      setSqlDbUrl("");
      setSqlQuery("");
      setScriptPath("");
      setHttpHeaders("");
      fetchCollectors();
    } catch (err: any) {
      toast({ title: "Failed to create collector", description: err.response?.data?.detail || "An error occurred.", variant: "error" });
    }
  };

  const handleDeleteCollector = async (id: string) => {
    try {
      await apiClient.delete(`/evidence-collectors/${id}`);
      toast({ title: "Collector Deleted" });
      fetchCollectors();
      if (activeCollector?.id === id) {
        setActiveCollector(null);
        setEvidenceLogs([]);
      }
    } catch (err: any) {
      toast({ title: "Delete failed", description: err.response?.data?.detail || "An error occurred.", variant: "error" });
    }
  };

  const handleRunCollector = async (id: string) => {
    toast({ title: "Execution Triggered", description: "Evidence collection started in background." });
    try {
      await apiClient.post(`/evidence-collectors/${id}/run`);
      toast({ title: "Run Succeeded", description: "Successfully fetched new evidence logs.", variant: "success" });
      fetchCollectors();
      if (activeCollector?.id === id) {
        fetchCollectorEvidence(id);
      }
    } catch (err: any) {
      toast({ title: "Execution failed", description: err.response?.data?.detail || "An error occurred.", variant: "error" });
    }
  };

  const fetchCollectorEvidence = async (id: string) => {
    const coll = collectors.find(c => c.id === id);
    if (coll) {
      setActiveCollector(coll);
    }
    setLoadingLogs(true);
    try {
      const { data } = await apiClient.get<EvidenceLog[]>(`/evidence-collectors/${id}/results`);
      setEvidenceLogs(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingLogs(false);
    }
  };

  return (
    <div className="space-y-5">
      <PageHeader
        eyebrow="Compliance Evidence Automation"
        title="Live Evidence Collectors"
        description="Schedule agentic scripts, database queries, and REST APIs to fetch and register external compliance evidence automatically."
      />

      <div className="grid gap-5 xl:grid-cols-[1fr_420px]">
        {/* Main Collectors Library */}
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <h3 className="font-semibold text-lg text-foreground flex items-center gap-2">
              <Server className="h-5 w-5 text-brand" /> Collectors Registry
            </h3>
            <div className="flex gap-2">
              <Button onClick={fetchCollectors} variant="secondary" size="sm">
                <RefreshCw className="h-4 w-4" />
              </Button>
              <Button onClick={() => setShowAddForm(!showAddForm)} size="sm">
                <Plus className="h-4 w-4 mr-2" /> {showAddForm ? "Show Registry" : "Add Collector"}
              </Button>
            </div>
          </div>

          {showAddForm ? (
            <Card>
              <CardHeader>
                <CardTitle>Create Evidence Collector</CardTitle>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleCreateCollector} className="space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs text-muted uppercase tracking-wider mb-1">Collector Name</label>
                      <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. AWS Secrets Manager Scanner" />
                    </div>
                    <div>
                      <label className="block text-xs text-muted uppercase tracking-wider mb-1">Collector Type</label>
                      <select
                        value={type}
                        onChange={(e: any) => setType(e.target.value)}
                        className="h-11 w-full rounded-lg border border-line bg-elevated px-3 text-sm outline-none focus:border-info/70"
                      >
                        <option value="http">HTTP / REST API</option>
                        <option value="sql">SQL Database Query</option>
                        <option value="script">Local Python/Shell Script</option>
                      </select>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs text-muted uppercase tracking-wider mb-1">Refreshed Schedule (Cron)</label>
                      <Input value={schedule} onChange={(e) => setSchedule(e.target.value)} placeholder="e.g. 0 */12 * * *" />
                    </div>
                    <div>
                      <label className="block text-xs text-muted uppercase tracking-wider mb-1">Target Compliance Domain</label>
                      <Input value={targetDomain} onChange={(e) => setTargetDomain(e.target.value)} placeholder="e.g. GDPR, Security" />
                    </div>
                  </div>

                  {/* Type Specific Fields */}
                  {type === "http" && (
                    <div className="space-y-4 bg-white/5 p-4 rounded-lg border border-white/10">
                      <div className="grid grid-cols-[100px_1fr] gap-2">
                        <select
                          value={httpMethod}
                          onChange={(e) => setHttpMethod(e.target.value)}
                          className="h-11 rounded-lg border border-line bg-elevated px-2 text-sm outline-none focus:border-info/70"
                        >
                          <option value="GET">GET</option>
                          <option value="POST">POST</option>
                        </select>
                        <Input value={httpUrl} onChange={(e) => setHttpUrl(e.target.value)} placeholder="https://api.github.com/repos/..." />
                      </div>
                      <div>
                        <label className="block text-xs text-muted uppercase tracking-wider mb-1">Headers JSON (Optional)</label>
                        <textarea
                          rows={2}
                          value={httpHeaders}
                          onChange={(e) => setHttpHeaders(e.target.value)}
                          placeholder='{"Authorization": "Bearer ${GITHUB_TOKEN}"}'
                          className="w-full bg-background border border-white/10 text-foreground text-sm rounded p-2 focus:border-brand outline-none"
                        />
                      </div>
                    </div>
                  )}

                  {type === "sql" && (
                    <div className="space-y-4 bg-white/5 p-4 rounded-lg border border-white/10">
                      <div>
                        <label className="block text-xs text-muted uppercase tracking-wider mb-1">DB Connection String (db_url)</label>
                        <Input value={sqlDbUrl} onChange={(e) => setSqlDbUrl(e.target.value)} placeholder="postgresql+psycopg://user:pass@host:port/db" />
                      </div>
                      <div>
                        <label className="block text-xs text-muted uppercase tracking-wider mb-1">SQL SELECT Query</label>
                        <textarea
                          rows={3}
                          value={sqlQuery}
                          onChange={(e) => setSqlQuery(e.target.value)}
                          placeholder="SELECT id, username AS citation_label, details AS evidence_text FROM users_log"
                          className="w-full bg-background border border-white/10 text-foreground text-sm rounded p-2 focus:border-brand outline-none font-mono"
                        />
                      </div>
                    </div>
                  )}

                  {type === "script" && (
                    <div className="space-y-4 bg-white/5 p-4 rounded-lg border border-white/10">
                      <div>
                        <label className="block text-xs text-muted uppercase tracking-wider mb-1">Script Path (System Absolute Path)</label>
                        <Input value={scriptPath} onChange={(e) => setScriptPath(e.target.value)} placeholder="C:/scripts/fetch_logs.py" />
                      </div>
                    </div>
                  )}

                  {/* Mapping Fields */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 bg-white/5 p-4 rounded-lg border border-white/10">
                    <div>
                      <label className="block text-xs text-muted uppercase tracking-wider mb-1">Evidence Text Selector (JSON Path)</label>
                      <Input value={mappingEvidenceText} onChange={(e) => setMappingEvidenceText(e.target.value)} placeholder="$.alerts[0].message" />
                    </div>
                    <div>
                      <label className="block text-xs text-muted uppercase tracking-wider mb-1">Citation Label Selector</label>
                      <Input value={mappingCitationLabel} onChange={(e) => setMappingCitationLabel(e.target.value)} placeholder="$.alerts[0].title" />
                    </div>
                  </div>

                  <Button type="submit" className="w-full">
                    Configure Collector
                  </Button>
                </form>
              </CardContent>
            </Card>
          ) : (
            <div className="grid grid-cols-1 gap-4">
              {loading && <div className="text-center py-6 text-muted">Retrieving active collectors...</div>}
              {!loading && collectors.length === 0 && (
                <div className="text-center p-8 text-muted border border-dashed border-line rounded-lg bg-panel">
                  No evidence collectors configured yet. Build one to pull real-time audit files.
                </div>
              )}
              {collectors.map((c) => {
                const isActive = activeCollector?.id === c.id;

                let Icon = Globe;
                if (c.collector_type === "sql") Icon = Database;
                if (c.collector_type === "script") Icon = FileCode;

                return (
                  <article
                    key={c.id}
                    onClick={() => fetchCollectorEvidence(c.id)}
                    className={cn(
                      "glass-panel border p-4 rounded-lg cursor-pointer transition-all hover:bg-white/5 flex flex-col md:flex-row justify-between items-start md:items-center gap-4",
                      isActive ? "border-brand" : "border-line"
                    )}
                  >
                    <div className="flex items-start gap-3">
                      <div className="h-10 w-10 shrink-0 rounded-lg bg-brand/10 text-brand border border-brand/20 grid place-items-center">
                        <Icon className="h-5 w-5" />
                      </div>
                      <div>
                        <h4 className="font-semibold text-foreground text-sm">{c.name}</h4>
                        <div className="flex flex-wrap gap-2 mt-1.5 text-xs text-muted items-center">
                          <span className="bg-white/5 border border-white/10 px-2 py-0.5 rounded uppercase font-bold text-[9px]">
                            {c.collector_type}
                          </span>
                          <span className="flex items-center gap-1">
                            <Calendar className="h-3 w-3" /> {c.schedule || "Manual only"}
                          </span>
                          <span>| Domain: {c.target_domain || "General"}</span>
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-2 self-end md:self-auto">
                      <span className={cn(
                        "text-[10px] font-bold px-2 py-0.5 rounded border mr-2 uppercase",
                        c.last_run_status === "success" ? "bg-success/20 text-success border-success/30" :
                        c.last_run_status === "failed" ? "bg-critical/20 text-critical border-critical/30" :
                        "bg-muted/10 text-muted border-white/10"
                      )}>
                        {c.last_run_status || "Never Run"}
                      </span>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleRunCollector(c.id);
                        }}
                        className="h-8 w-8 rounded-lg bg-brand/10 hover:bg-brand/20 border border-brand/30 grid place-items-center text-brand transition-all"
                        title="Run Now"
                      >
                        <Play className="h-4 w-4" />
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDeleteCollector(c.id);
                        }}
                        className="h-8 w-8 rounded-lg bg-critical/10 hover:bg-critical/20 border border-critical/30 grid place-items-center text-critical transition-all"
                        title="Delete"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </article>
                );
              })}
            </div>
          )}
        </div>

        {/* Collected Evidence Trail Panel */}
        <div className="space-y-4">
          <h3 className="font-semibold text-lg text-foreground flex items-center gap-2">
            <Activity className="h-5 w-5 text-brand" /> Collected Trace Logs
          </h3>

          <Card className="h-[600px] flex flex-col">
            <CardHeader className="border-b border-line shrink-0">
              <CardTitle className="text-sm font-semibold text-muted">
                {activeCollector ? `Log history for: ${activeCollector.name}` : "Select a collector to view logs"}
              </CardTitle>
            </CardHeader>
            <CardContent className="flex-1 overflow-y-auto p-4 space-y-3">
              {loadingLogs && (
                <div className="flex flex-col items-center justify-center h-48 text-muted">
                  <Loader2 className="h-6 w-6 border-2 border-brand border-t-transparent rounded-full animate-spin mb-2" />
                  <p className="text-sm">Retrieving evidence trace...</p>
                </div>
              )}

              {!loadingLogs && !activeCollector && (
                <div className="text-center text-muted h-48 flex flex-col justify-center">
                  <Search className="h-8 w-8 mx-auto mb-2 opacity-40" />
                  <p className="text-xs">Select any collector from the list to see parsed compliance evidence logs.</p>
                </div>
              )}

              {!loadingLogs && activeCollector && evidenceLogs.length === 0 && (
                <div className="text-center text-muted h-48 flex flex-col justify-center">
                  <Play className="h-8 w-8 mx-auto mb-2 opacity-40 text-brand" />
                  <p className="text-sm">No evidence collected yet.</p>
                  <p className="text-xs mt-1">Click the play icon on the collector row to execute a scan.</p>
                </div>
              )}

              {!loadingLogs && activeCollector && evidenceLogs.length > 0 && (
                <div className="space-y-3">
                  {evidenceLogs.map((log) => (
                    <div key={log.id} className="border border-white/10 rounded-lg p-3 bg-white/5 space-y-2">
                      <div className="flex justify-between items-center text-[10px] font-bold text-muted uppercase tracking-wider">
                        <span className="text-cyan">{log.citation_label}</span>
                        <span>{new Date(log.collected_at).toLocaleDateString()}</span>
                      </div>
                      <p className="text-xs text-foreground/80 leading-relaxed font-sans">
                        {log.evidence_text}
                      </p>
                      <div className="flex justify-between items-center text-[10px] text-muted">
                        <span>Confidence: {(log.confidence_score * 100).toFixed(0)}%</span>
                        <span className="font-mono text-[9px]">{log.source_type}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
