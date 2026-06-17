"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import {
  ArrowLeft,
  Check,
  Download,
  FileDown,
  FileText,
  LayoutTemplate,
  Loader2,
  RefreshCw,
  Save,
  Settings,
  Wand2,
} from "lucide-react";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useToast } from "@/components/ui/toast";
import {
  generateCustomReport,
  getAudit,
  getCustomReport,
  updateCustomReport,
  downloadCustomReport,
  type CustomReport,
} from "@/services/audits/audit-service";
import { getErrorMessage } from "@/services/api/client";

const TEMPLATE_OPTIONS = [
  { value: "Executive", label: "Executive Summary", description: "Concise summary focusing on strategic business risks and compliance score highlights." },
  { value: "Board", label: "Board Presentation", description: "Governance-focused overview of risk exposure, mitigation costs, and timelines." },
  { value: "Auditor", label: "Auditor-Ready", description: "Formal, detailed documentation referencing specific rules and compliance citations." },
  { value: "Technical", label: "Technical Detail", description: "Developer-oriented breakdown detailing code/policy violations and action items." },
];

const SECTION_OPTIONS = [
  { value: "Overview", label: "Overview", description: "Introduction, summary of audit rating, and overall health status." },
  { value: "Findings Summary", label: "Findings Summary", description: "Detailed look at non-compliant rules, explanations, and risk severity." },
  { value: "Remediation Plans", label: "Remediation Plans", description: "Actionable steps, estimated effort hours, priorities, and owners." },
  { value: "Evidence Appendix", label: "Evidence Appendix", description: "Granular citations and raw evidence mappings from the source text." },
];

export default function CustomReportBuilderPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const { toast } = useToast();
  const auditId = params.id;

  const [selectedTemplate, setSelectedTemplate] = useState("Executive");
  const [selectedSections, setSelectedSections] = useState<string[]>([
    "Overview",
    "Findings Summary",
    "Remediation Plans",
  ]);

  const [customReport, setCustomReport] = useState<CustomReport | null>(null);
  const [editedSections, setEditedSections] = useState<Record<string, string>>({});
  const [activePreviewTab, setActivePreviewTab] = useState<string>("");

  // Fetch parent audit details
  const auditQuery = useQuery({
    queryKey: ["audit", auditId],
    queryFn: () => getAudit(auditId),
    enabled: Boolean(auditId),
  });

  // Generate mutation
  const generateMutation = useMutation({
    mutationFn: () =>
      generateCustomReport(auditId, {
        template: selectedTemplate,
        sections: selectedSections,
      }),
    onSuccess: (data) => {
      setCustomReport(data);
      setEditedSections(data.generated_json.sections || {});
      const firstSection = Object.keys(data.generated_json.sections || {})[0] || "";
      setActivePreviewTab(firstSection);
      toast({ title: "Report generated", description: "The AI agent has rewritten the report narratives." });
    },
    onError: (err) => {
      toast({
        title: "Generation failed",
        description: getErrorMessage(err),
        variant: "error",
      });
    },
  });

  // Save/Update mutation
  const saveMutation = useMutation({
    mutationFn: () => {
      if (!customReport) throw new Error("No report to save");
      const updatedJson = {
        ...customReport.generated_json,
        sections: editedSections,
      };
      return updateCustomReport(customReport.id, { generated_json: updatedJson });
    },
    onSuccess: (data) => {
      setCustomReport(data);
      toast({ title: "Changes saved", description: "Report edits stored successfully." });
    },
    onError: (err) => {
      toast({
        title: "Save failed",
        description: getErrorMessage(err),
        variant: "error",
      });
    },
  });

  // Download PDF
  const downloadPdfMutation = useMutation({
    mutationFn: () => {
      if (!customReport) throw new Error("No report");
      return downloadCustomReport(customReport.id, "pdf");
    },
    onSuccess: (blob) => {
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `custom-report-${auditId}-${selectedTemplate.toLowerCase()}.pdf`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
    },
    onError: (err) => toast({ title: "PDF export failed", description: getErrorMessage(err), variant: "error" }),
  });

  // Download DOCX
  const downloadDocxMutation = useMutation({
    mutationFn: () => {
      if (!customReport) throw new Error("No report");
      return downloadCustomReport(customReport.id, "docx");
    },
    onSuccess: (blob) => {
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `custom-report-${auditId}-${selectedTemplate.toLowerCase()}.docx`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
    },
    onError: (err) => toast({ title: "DOCX export failed", description: getErrorMessage(err), variant: "error" }),
  });

  const handleSectionToggle = (section: string) => {
    setSelectedSections((prev) =>
      prev.includes(section)
        ? prev.filter((s) => s !== section)
        : [...prev, section]
    );
  };

  const handleSectionTextChange = (section: string, text: string) => {
    setEditedSections((prev) => ({
      ...prev,
      [section]: text,
    }));
  };

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Compliance Intelligence"
        title="AI Custom Report Builder"
        description="Rewrite raw audit findings into audience-tailored summaries for board presentations, audit reviews, or technical engineering."
        actions={
          <Button variant="secondary" onClick={() => router.push(`/admin/reports/${auditId}`)}>
            <ArrowLeft className="h-4 w-4 mr-2" /> Back to Results
          </Button>
        }
      />

      <div className="grid gap-6 xl:grid-cols-[400px_1fr]">
        {/* Left Column: Config Panel */}
        <div className="space-y-6">
          <Card className="border-line bg-panel/60 backdrop-blur-xl">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Settings className="h-5 w-5 text-cyan" />
                Configure Report
              </CardTitle>
              <p className="text-xs text-muted">Select template type and sections to generate.</p>
            </CardHeader>
            <CardContent className="space-y-5">
              {/* Template Select */}
              <div className="space-y-2.5">
                <label className="text-xs font-semibold uppercase tracking-wider text-muted">
                  Audience Template
                </label>
                <div className="space-y-2">
                  {TEMPLATE_OPTIONS.map((opt) => (
                    <button
                      key={opt.value}
                      onClick={() => setSelectedTemplate(opt.value)}
                      className={`w-full text-left p-3 rounded-lg border transition text-sm flex flex-col gap-1 ${
                        selectedTemplate === opt.value
                          ? "border-cyan/50 bg-cyan/10 text-cyan shadow-[0_0_15px_rgba(0,229,255,0.08)]"
                          : "border-line bg-elevated/40 hover:bg-elevated text-muted hover:text-foreground"
                      }`}
                    >
                      <span className="font-semibold">{opt.label}</span>
                      <span className="text-xs opacity-75">{opt.description}</span>
                    </button>
                  ))}
                </div>
              </div>

              {/* Sections Select */}
              <div className="space-y-2.5">
                <label className="text-xs font-semibold uppercase tracking-wider text-muted">
                  Sections to Include
                </label>
                <div className="space-y-2">
                  {SECTION_OPTIONS.map((opt) => {
                    const included = selectedSections.includes(opt.value);
                    return (
                      <button
                        key={opt.value}
                        onClick={() => handleSectionToggle(opt.value)}
                        className={`w-full text-left p-3 rounded-lg border transition text-sm flex items-center justify-between gap-3 ${
                          included
                            ? "border-cyan/35 bg-cyan/5 text-foreground font-medium"
                            : "border-line bg-elevated/20 text-muted hover:text-foreground"
                        }`}
                      >
                        <div className="flex flex-col gap-0.5">
                          <span>{opt.label}</span>
                          <span className="text-[11px] opacity-75">{opt.description}</span>
                        </div>
                        <div
                          className={`h-5 w-5 rounded border flex items-center justify-center shrink-0 transition ${
                            included
                              ? "border-cyan bg-cyan text-background"
                              : "border-muted/30"
                          }`}
                        >
                          {included && <Check className="h-3.5 w-3.5" />}
                        </div>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Generate Trigger */}
              <Button
                className="w-full bg-cyan hover:bg-cyan/90 text-background font-semibold"
                size="lg"
                disabled={selectedSections.length === 0 || generateMutation.isPending}
                onClick={() => generateMutation.mutate()}
              >
                {generateMutation.isPending ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Rewriting Report...
                  </>
                ) : (
                  <>
                    <Wand2 className="mr-2 h-4 w-4" />
                    Generate AI Report
                  </>
                )}
              </Button>
            </CardContent>
          </Card>
        </div>

        {/* Right Column: Preview & Editor */}
        <div className="space-y-6">
          {!customReport ? (
            <Card className="border-dashed border-line bg-panel/30 h-[600px] flex flex-col items-center justify-center text-center p-6">
              <Wand2 className="h-12 w-12 text-muted/40 mb-4 animate-pulse" />
              <CardTitle className="text-muted">No custom report generated yet</CardTitle>
              <p className="text-xs text-muted max-w-md mt-2">
                Configure your target template and section components in the left panel, then run the AI engine to generate narrative revisions.
              </p>
            </Card>
          ) : (
            <Card className="border-line bg-panel/60 backdrop-blur-xl flex flex-col h-[750px]">
              <CardHeader className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-line pb-4">
                <div>
                  <CardTitle className="text-cyan">{customReport.generated_json.title}</CardTitle>
                  <p className="text-xs text-muted">
                    Tailored for: {selectedTemplate} audience. Edit section markdown directly below.
                  </p>
                </div>

                <div className="flex flex-wrap gap-2 shrink-0">
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => saveMutation.mutate()}
                    disabled={saveMutation.isPending}
                  >
                    {saveMutation.isPending ? (
                      <Loader2 className="h-4 w-4 animate-spin mr-1" />
                    ) : (
                      <Save className="h-4 w-4 mr-1 text-cyan" />
                    )}
                    Save Edits
                  </Button>
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => downloadPdfMutation.mutate()}
                    disabled={downloadPdfMutation.isPending}
                  >
                    {downloadPdfMutation.isPending ? (
                      <Loader2 className="h-4 w-4 animate-spin mr-1" />
                    ) : (
                      <FileDown className="h-4 w-4 mr-1 text-red-400" />
                    )}
                    PDF
                  </Button>
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => downloadDocxMutation.mutate()}
                    disabled={downloadDocxMutation.isPending}
                  >
                    {downloadDocxMutation.isPending ? (
                      <Loader2 className="h-4 w-4 animate-spin mr-1" />
                    ) : (
                      <Download className="h-4 w-4 mr-1 text-blue-400" />
                    )}
                    Word (DOCX)
                  </Button>
                </div>
              </CardHeader>

              {/* Tab Navigation */}
              <div className="border-b border-line bg-elevated/40 flex overflow-x-auto shrink-0">
                {Object.keys(editedSections).map((sec) => (
                  <button
                    key={sec}
                    onClick={() => setActivePreviewTab(sec)}
                    className={`px-5 py-3 text-xs font-semibold uppercase tracking-wider border-b-2 whitespace-nowrap transition-all ${
                      activePreviewTab === sec
                        ? "border-cyan text-cyan bg-cyan/5"
                        : "border-transparent text-muted hover:text-foreground"
                    }`}
                  >
                    {sec}
                  </button>
                ))}
              </div>

              {/* Content Panel */}
              <div className="flex-1 p-5 min-h-0 flex flex-col">
                {activePreviewTab && (
                  <div className="flex-1 flex flex-col min-h-0 space-y-4">
                    <div className="flex items-center justify-between text-xs text-muted font-medium shrink-0">
                      <span>Markdown Editor</span>
                      <span>Auto-saved locally on save action</span>
                    </div>
                    <textarea
                      value={editedSections[activePreviewTab] || ""}
                      onChange={(e) => handleSectionTextChange(activePreviewTab, e.target.value)}
                      className="flex-1 w-full bg-black/35 rounded-lg border border-line p-4 text-sm font-mono leading-relaxed outline-none focus:border-cyan/50 resize-none overflow-y-auto"
                      placeholder="Write your markdown summary here..."
                    />
                  </div>
                )}
              </div>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
