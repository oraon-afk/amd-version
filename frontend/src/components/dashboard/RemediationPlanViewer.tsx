"use client";

import React, { useEffect, useState } from "react";
import { useAuth } from "@/providers/auth-provider";
import { getRemediationPlan, updateRemediationPlan } from "@/services/audits/audit-service";
import { 
  Clock, 
  UserCheck, 
  AlertCircle, 
  CheckCircle2, 
  ListChecks, 
  Plus, 
  Trash2, 
  Edit, 
  Save, 
  X, 
  ShieldCheck, 
  ShieldAlert 
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

interface RemediationPlanData {
  id: string;
  finding_id: string;
  steps: string[];
  estimated_effort_hours: number;
  priority: string;
  suggested_owner_role: string;
  approved: boolean;
  created_at: string;
}

interface RemediationPlanViewerProps {
  findingId: string;
}

export function RemediationPlanViewer({ findingId }: RemediationPlanViewerProps) {
  const { user } = useAuth();
  const isPrivileged = user?.role?.toUpperCase() === "ADMIN" || user?.role?.toUpperCase() === "REVIEWER";

  const [plan, setPlan] = useState<RemediationPlanData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Edit states
  const [isEditing, setIsEditing] = useState(false);
  const [editedSteps, setEditedSteps] = useState<string[]>([]);
  const [editedEffort, setEditedEffort] = useState<number>(0);
  const [editedPriority, setEditedPriority] = useState<string>("MEDIUM");
  const [editedOwner, setEditedOwner] = useState<string>("");
  const [newStepText, setNewStepText] = useState<string>("");

  const fetchPlan = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getRemediationPlan(findingId);
      setPlan(data);
      setEditedSteps(data.steps);
      setEditedEffort(data.estimated_effort_hours);
      setEditedPriority(data.priority);
      setEditedOwner(data.suggested_owner_role);
    } catch (err: any) {
      setError("Failed to load or generate remediation plan.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (findingId) {
      fetchPlan();
    }
  }, [findingId]);

  const handleSave = async () => {
    if (!plan) return;
    setLoading(true);
    try {
      const updated = await updateRemediationPlan(findingId, {
        steps: editedSteps,
        estimated_effort_hours: editedEffort,
        priority: editedPriority,
        suggested_owner_role: editedOwner,
      });
      setPlan(updated);
      setIsEditing(false);
    } catch (err: any) {
      setError("Failed to save remediation plan changes.");
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = async () => {
    if (!plan) return;
    setLoading(true);
    try {
      const updated = await updateRemediationPlan(findingId, {
        approved: !plan.approved,
      });
      setPlan(updated);
    } catch (err: any) {
      setError("Failed to update approval status.");
    } finally {
      setLoading(false);
    }
  };

  const handleAddStep = () => {
    if (!newStepText.trim()) return;
    setEditedSteps([...editedSteps, newStepText.trim()]);
    setNewStepText("");
  };

  const handleRemoveStep = (index: number) => {
    setEditedSteps(editedSteps.filter((_, idx) => idx !== index));
  };

  const handleStepTextChange = (index: number, val: string) => {
    const updated = [...editedSteps];
    updated[index] = val;
    setEditedSteps(updated);
  };

  if (loading && !plan) {
    return (
      <div className="flex items-center justify-center p-6 text-xs text-muted">
        <div className="h-4 w-4 border-2 border-brand border-t-transparent rounded-full animate-spin mr-2" />
        Generating remediation plan...
      </div>
    );
  }

  if (error && !plan) {
    return (
      <div className="p-4 rounded-lg bg-critical/10 border border-critical/20 text-xs text-critical flex items-center gap-2">
        <AlertCircle className="h-4 w-4 shrink-0" />
        {error}
      </div>
    );
  }

  if (!plan) return null;

  return (
    <div className="mt-4 rounded-lg border border-line bg-black/20 overflow-hidden">
      {/* Header Panel */}
      <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-3 bg-white/5 border-b border-line">
        <span className="flex items-center gap-2 text-sm font-semibold">
          <ListChecks className="h-4 w-4 text-brand" />
          AI Remediation Plan
          {plan.approved ? (
            <span className="flex items-center gap-1 text-[10px] font-bold uppercase tracking-wider bg-success/20 text-success border border-success/30 px-1.5 py-0.5 rounded">
              <ShieldCheck className="h-3 w-3" /> Approved Plan
            </span>
          ) : (
            <span className="flex items-center gap-1 text-[10px] font-bold uppercase tracking-wider bg-warning/20 text-warning border border-warning/30 px-1.5 py-0.5 rounded">
              <ShieldAlert className="h-3 w-3" /> Draft Plan
            </span>
          )}
        </span>

        {isPrivileged && (
          <div className="flex gap-2">
            {!isEditing ? (
              <>
                <Button size="sm" variant="secondary" onClick={() => setIsEditing(true)}>
                  <Edit className="h-3.5 w-3.5 mr-1" /> Edit
                </Button>
                <Button 
                  size="sm" 
                  variant={plan.approved ? "secondary" : "default"}
                  className={!plan.approved ? "bg-success hover:bg-success/90 text-white" : ""}
                  onClick={handleApprove}
                >
                  <CheckCircle2 className="h-3.5 w-3.5 mr-1" /> {plan.approved ? "Revoke Approval" : "Approve Plan"}
                </Button>
              </>
            ) : (
              <>
                <Button size="sm" variant="secondary" onClick={() => setIsEditing(false)}>
                  <X className="h-3.5 w-3.5 mr-1" /> Cancel
                </Button>
                <Button size="sm" variant="default" className="bg-brand text-white" onClick={handleSave}>
                  <Save className="h-3.5 w-3.5 mr-1" /> Save
                </Button>
              </>
            )}
          </div>
        )}
      </div>

      {/* Main Body */}
      <div className="p-4 space-y-4">
        {/* Metadata widgets */}
        {!isEditing ? (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <div className="flex items-center gap-3 bg-white/5 border border-line p-3 rounded-lg text-sm">
              <Clock className="h-4 w-4 text-muted shrink-0" />
              <div>
                <div className="text-[10px] text-muted font-bold uppercase">Estimated Effort</div>
                <div className="font-semibold text-foreground">{plan.estimated_effort_hours} Hours</div>
              </div>
            </div>
            <div className="flex items-center gap-3 bg-white/5 border border-line p-3 rounded-lg text-sm">
              <AlertCircle className="h-4 w-4 text-muted shrink-0" />
              <div>
                <div className="text-[10px] text-muted font-bold uppercase">Execution Priority</div>
                <Badge variant={plan.priority === "HIGH" ? "critical" : plan.priority === "MEDIUM" ? "medium" : "low"}>
                  {plan.priority}
                </Badge>
              </div>
            </div>
            <div className="flex items-center gap-3 bg-white/5 border border-line p-3 rounded-lg text-sm">
              <UserCheck className="h-4 w-4 text-muted shrink-0" />
              <div>
                <div className="text-[10px] text-muted font-bold uppercase">Suggested Owner Role</div>
                <div className="font-semibold text-foreground">{plan.suggested_owner_role}</div>
              </div>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 bg-white/5 border border-white/10 p-3 rounded-lg">
            <div>
              <label className="block text-[10px] text-muted font-bold uppercase mb-1">Estimated Effort (Hours)</label>
              <input 
                type="number" 
                value={editedEffort} 
                onChange={(e) => setEditedEffort(parseInt(e.target.value) || 0)}
                className="w-full bg-background border border-white/10 text-foreground text-sm rounded p-1.5 focus:border-brand outline-none"
              />
            </div>
            <div>
              <label className="block text-[10px] text-muted font-bold uppercase mb-1">Priority</label>
              <select 
                value={editedPriority} 
                onChange={(e) => setEditedPriority(e.target.value)}
                className="w-full bg-background border border-white/10 text-foreground text-sm rounded p-1.5 focus:border-brand outline-none"
              >
                <option value="LOW">Low</option>
                <option value="MEDIUM">Medium</option>
                <option value="HIGH">High</option>
              </select>
            </div>
            <div>
              <label className="block text-[10px] text-muted font-bold uppercase mb-1">Suggested Owner Role</label>
              <input 
                type="text" 
                value={editedOwner} 
                onChange={(e) => setEditedOwner(e.target.value)}
                className="w-full bg-background border border-white/10 text-foreground text-sm rounded p-1.5 focus:border-brand outline-none"
              />
            </div>
          </div>
        )}

        {/* Steps List */}
        <div className="space-y-2">
          <div className="text-xs font-semibold uppercase text-muted tracking-wider">Corrective Action Steps</div>
          
          <div className="space-y-2">
            {(!isEditing ? plan.steps : editedSteps).map((step, idx) => (
              <div key={idx} className="flex items-start gap-3 bg-white/5 border border-line p-3 rounded-lg text-sm">
                <span className="shrink-0 flex items-center justify-center h-5 w-5 rounded-full bg-brand/10 text-brand text-xs font-mono font-bold">
                  {idx + 1}
                </span>
                
                {!isEditing ? (
                  <span className="text-foreground/90">{step}</span>
                ) : (
                  <div className="flex-1 flex gap-2">
                    <input 
                      type="text" 
                      value={step}
                      onChange={(e) => handleStepTextChange(idx, e.target.value)}
                      className="flex-1 bg-background border border-white/10 text-foreground text-xs rounded p-1.5 focus:border-brand outline-none"
                    />
                    <button 
                      onClick={() => handleRemoveStep(idx)}
                      className="p-1.5 rounded bg-critical/10 text-critical border border-critical/20 hover:bg-critical/20"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>

          {isEditing && (
            <div className="flex gap-2 mt-3 p-3 bg-white/5 border border-white/10 rounded-lg">
              <input 
                type="text" 
                placeholder="Add new step action item..."
                value={newStepText}
                onChange={(e) => setNewStepText(e.target.value)}
                className="flex-1 bg-background border border-white/10 text-foreground text-xs rounded p-1.5 focus:border-brand outline-none"
              />
              <Button size="sm" variant="secondary" onClick={handleAddStep}>
                <Plus className="h-3.5 w-3.5 mr-1" /> Add Step
              </Button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
