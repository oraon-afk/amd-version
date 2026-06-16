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
  CheckCircle,
  Copy,
  Key,
  Plus,
  RefreshCw,
  Trash2,
  Webhook as WebhookIcon,
  XCircle,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface Webhook {
  id: string;
  name: string;
  url: string;
  events: string[];
  is_active: boolean;
  created_at: string;
  last_triggered_at: string | null;
}

interface WebhookDelivery {
  id: string;
  webhook_id: string;
  event: string;
  response_status: number | null;
  success: boolean;
  retry_count: number;
  created_at: string;
}

interface ApiKey {
  id: string;
  name: string;
  is_active: boolean;
  created_at: string;
  last_used_at: string | null;
  expires_at: string | null;
  raw_key?: string;
}

export default function WebhooksAdminPage() {
  const { toast } = useToast();
  const [activeTab, setActiveTab] = useState<"webhooks" | "apikeys">("webhooks");

  // Webhook States
  const [webhooks, setWebhooks] = useState<Webhook[]>([]);
  const [loadingWebhooks, setLoadingWebhooks] = useState(false);
  const [whName, setWhName] = useState("");
  const [whUrl, setWhUrl] = useState("");
  const [whSecret, setWhSecret] = useState("");
  const [selectedEvents, setSelectedEvents] = useState<string[]>([]);
  const [deliveries, setDeliveries] = useState<WebhookDelivery[]>([]);
  const [selectedWebhookId, setSelectedWebhookId] = useState<string | null>(null);

  // API Key States
  const [apiKeys, setApiKeys] = useState<ApiKey[]>([]);
  const [loadingKeys, setLoadingKeys] = useState(false);
  const [keyName, setKeyName] = useState("");
  const [newCreatedKey, setNewCreatedKey] = useState<string | null>(null);

  const availableEvents = [
    "audit.completed",
    "audit.pending_review",
    "finding.critical",
    "rule.changed",
  ];

  useEffect(() => {
    fetchWebhooks();
    fetchApiKeys();
  }, []);

  // ────────────────────────── Webhooks API ──────────────────────────────────

  const fetchWebhooks = async () => {
    setLoadingWebhooks(true);
    try {
      const { data } = await apiClient.get<any[]>("/admin/webhooks");
      setWebhooks(data.map(w => ({
        id: w.id,
        name: w.name,
        url: w.url,
        events: w.events,
        is_active: w.is_active,
        created_at: w.created_at,
        last_triggered_at: w.last_triggered_at,
      })));
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingWebhooks(false);
    }
  };

  const handleCreateWebhook = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!whName.trim() || !whUrl.trim() || selectedEvents.length === 0) {
      toast({ title: "Validation Error", description: "Name, URL and at least one event trigger are required.", variant: "error" });
      return;
    }

    try {
      await apiClient.post("/admin/webhooks", {
        name: whName,
        url: whUrl,
        events: selectedEvents,
        secret: whSecret.trim() || null,
      });
      toast({ title: "Webhook Configured", description: "The webhook endpoint has been successfully registered.", variant: "success" });
      setWhName("");
      setWhUrl("");
      setWhSecret("");
      setSelectedEvents([]);
      fetchWebhooks();
    } catch (err: any) {
      toast({ title: "Failed to create webhook", description: err.response?.data?.detail || "An error occurred.", variant: "error" });
    }
  };

  const handleDeleteWebhook = async (id: string) => {
    try {
      await apiClient.delete(`/admin/webhooks/${id}`);
      toast({ title: "Webhook Deleted" });
      fetchWebhooks();
      if (selectedWebhookId === id) {
        setSelectedWebhookId(null);
        setDeliveries([]);
      }
    } catch (err: any) {
      toast({ title: "Delete failed", description: err.response?.data?.detail || "An error occurred.", variant: "error" });
    }
  };

  const handleTestWebhook = async (id: string) => {
    try {
      const { data } = await apiClient.post(`/admin/webhooks/${id}/test`);
      toast({
        title: "Test Sent",
        description: `HTTP Status: ${data.response_status || "Unknown"} (Success: ${data.success ? "Yes" : "No"})`,
        variant: data.success ? "success" : "error",
      });
      fetchWebhooks();
      if (selectedWebhookId === id) {
        fetchDeliveries(id);
      }
    } catch (err: any) {
      toast({ title: "Test failed", description: err.response?.data?.detail || "An error occurred.", variant: "error" });
    }
  };

  const fetchDeliveries = async (webhookId: string) => {
    setSelectedWebhookId(webhookId);
    try {
      const { data } = await apiClient.get<WebhookDelivery[]>(`/admin/webhooks/${webhookId}/deliveries`);
      setDeliveries(data);
    } catch (err) {
      console.error(err);
    }
  };

  const handleToggleEvent = (event: string) => {
    if (selectedEvents.includes(event)) {
      setSelectedEvents(selectedEvents.filter(e => e !== event));
    } else {
      setSelectedEvents([...selectedEvents, event]);
    }
  };

  // ────────────────────────── API Keys API ──────────────────────────────────

  const fetchApiKeys = async () => {
    setLoadingKeys(true);
    try {
      const { data } = await apiClient.get<ApiKey[]>("/admin/api-keys");
      setApiKeys(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingKeys(false);
    }
  };

  const handleCreateApiKey = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!keyName.trim()) return;

    try {
      const { data } = await apiClient.post<ApiKey>("/admin/api-keys", {
        name: keyName,
      });
      toast({ title: "API Key Created", description: "Copy your key now. It will not be shown again.", variant: "success" });
      setNewCreatedKey(data.raw_key || null);
      setKeyName("");
      fetchApiKeys();
    } catch (err: any) {
      toast({ title: "Failed to create API key", description: err.response?.data?.detail || "An error occurred.", variant: "error" });
    }
  };

  const handleRevokeApiKey = async (id: string) => {
    try {
      await apiClient.delete(`/admin/api-keys/${id}`);
      toast({ title: "API Key Revoked" });
      fetchApiKeys();
    } catch (err: any) {
      toast({ title: "Revocation failed", description: err.response?.data?.detail || "An error occurred.", variant: "error" });
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    toast({ title: "Copied to clipboard" });
  };

  return (
    <div className="space-y-5">
      <PageHeader
        eyebrow="Integration Ecosystem"
        title="Open Integrations & API"
        description="Configure outbound webhooks to stream compliance events or provision API keys for automated CI/CD audits."
      />

      {/* Tabs */}
      <div className="flex border-b border-line gap-6">
        <button
          onClick={() => setActiveTab("webhooks")}
          className={cn(
            "pb-3 text-sm font-semibold tracking-wider uppercase border-b-2 transition-all flex items-center gap-1.5",
            activeTab === "webhooks"
              ? "border-brand text-brand"
              : "border-transparent text-muted hover:text-foreground"
          )}
        >
          <WebhookIcon className="h-4 w-4" /> Outbound Webhooks
        </button>
        <button
          onClick={() => setActiveTab("apikeys")}
          className={cn(
            "pb-3 text-sm font-semibold tracking-wider uppercase border-b-2 transition-all flex items-center gap-1.5",
            activeTab === "apikeys"
              ? "border-brand text-brand"
              : "border-transparent text-muted hover:text-foreground"
          )}
        >
          <Key className="h-4 w-4" /> Inbound API Keys
        </button>
      </div>

      {activeTab === "webhooks" ? (
        <div className="grid gap-5 xl:grid-cols-[430px_1fr]">
          {/* Create Webhook Column */}
          <div className="space-y-5">
            <Card>
              <CardHeader>
                <CardTitle>Configure Outbound Webhook</CardTitle>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleCreateWebhook} className="space-y-4">
                  <div>
                    <label className="block text-xs text-muted uppercase tracking-wider mb-1">Friendly Name</label>
                    <Input
                      value={whName}
                      onChange={(e) => setWhName(e.target.value)}
                      placeholder="e.g. Slack Notifications"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-muted uppercase tracking-wider mb-1">Target Endpoint URL</label>
                    <Input
                      value={whUrl}
                      onChange={(e) => setWhUrl(e.target.value)}
                      placeholder="https://api.company.com/webhook"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-muted uppercase tracking-wider mb-1">Verification Secret Token (Optional)</label>
                    <Input
                      type="password"
                      value={whSecret}
                      onChange={(e) => setWhSecret(e.target.value)}
                      placeholder="Signing key secret"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-muted uppercase tracking-wider mb-2">Event Triggers</label>
                    <div className="space-y-2">
                      {availableEvents.map((event) => (
                        <label key={event} className="flex items-center gap-2 text-sm text-foreground/80 cursor-pointer">
                          <input
                            type="checkbox"
                            checked={selectedEvents.includes(event)}
                            onChange={() => handleToggleEvent(event)}
                            className="rounded border-white/10 bg-elevated text-brand focus:ring-brand"
                          />
                          <span>{event}</span>
                        </label>
                      ))}
                    </div>
                  </div>
                  <Button type="submit" className="w-full">
                    <Plus className="h-4 w-4 mr-2" /> Add Webhook
                  </Button>
                </form>
              </CardContent>
            </Card>
          </div>

          {/* Webhooks Library Column */}
          <div className="space-y-5">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle>Configured Outbound Endpoints</CardTitle>
                <button onClick={fetchWebhooks} className="text-muted hover:text-foreground">
                  <RefreshCw className="h-4 w-4" />
                </button>
              </CardHeader>
              <CardContent className="space-y-4">
                {loadingWebhooks && <div className="text-center p-4 text-muted">Loading webhooks...</div>}
                {!loadingWebhooks && webhooks.length === 0 && (
                  <div className="text-center p-8 text-muted border border-dashed border-line rounded-lg">
                    No webhooks configured yet. Configure one on the left to start streaming events.
                  </div>
                )}
                {webhooks.map((wh) => (
                  <article
                    key={wh.id}
                    onClick={() => fetchDeliveries(wh.id)}
                    className={cn(
                      "rounded-lg border bg-elevated p-4 cursor-pointer transition-all hover:bg-white/5",
                      selectedWebhookId === wh.id ? "border-brand" : "border-line"
                    )}
                  >
                    <div className="flex justify-between items-start mb-2">
                      <div>
                        <h4 className="font-semibold text-foreground text-sm">{wh.name}</h4>
                        <p className="text-xs text-muted mt-1 font-mono break-all">{wh.url}</p>
                      </div>
                      <div className="flex items-center gap-2">
                        <Button
                          size="sm"
                          variant="secondary"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleTestWebhook(wh.id);
                          }}
                        >
                          Test
                        </Button>
                        <Button
                          size="sm"
                          variant="destructive"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleDeleteWebhook(wh.id);
                          }}
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </Button>
                      </div>
                    </div>
                    <div className="flex flex-wrap gap-1.5 mt-3">
                      {wh.events.map((evt) => (
                        <span key={evt} className="text-[10px] bg-white/5 border border-white/10 px-2 py-0.5 rounded text-muted font-mono">
                          {evt}
                        </span>
                      ))}
                    </div>
                  </article>
                ))}
              </CardContent>
            </Card>

            {/* Delivery Logs Panel */}
            {selectedWebhookId && (
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm uppercase tracking-wider text-muted flex items-center gap-2">
                    <Activity className="h-4 w-4 text-brand" /> Delivery History logs
                  </CardTitle>
                </CardHeader>
                <CardContent className="max-h-60 overflow-y-auto space-y-2">
                  {deliveries.length === 0 && (
                    <p className="text-xs text-muted text-center py-4">No delivery attempts recorded yet. Click Test above to trigger one.</p>
                  )}
                  {deliveries.map((d) => (
                    <div key={d.id} className="flex justify-between items-center text-xs bg-white/5 p-2.5 rounded border border-white/5">
                      <div className="flex items-center gap-2">
                        {d.success ? (
                          <CheckCircle className="h-4 w-4 text-success" />
                        ) : (
                          <XCircle className="h-4 w-4 text-critical" />
                        )}
                        <div>
                          <p className="font-semibold text-foreground">{d.event}</p>
                          <p className="text-[10px] text-muted">{new Date(d.created_at).toLocaleString()}</p>
                        </div>
                      </div>
                      <div className="text-right">
                        <span className={cn(
                          "px-2 py-0.5 rounded text-[10px] font-bold",
                          d.success ? "bg-success/20 text-success" : "bg-critical/20 text-critical"
                        )}>
                          HTTP {d.response_status || "ERR"}
                        </span>
                        <p className="text-[10px] text-muted mt-1">Retries: {d.retry_count}</p>
                      </div>
                    </div>
                  ))}
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      ) : (
        <div className="grid gap-5 xl:grid-cols-[430px_1fr]">
          {/* Provision Keys Column */}
          <div className="space-y-5">
            <Card>
              <CardHeader>
                <CardTitle>Provision API Key</CardTitle>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleCreateApiKey} className="space-y-4">
                  <div>
                    <label className="block text-xs text-muted uppercase tracking-wider mb-1">Key Description / Name</label>
                    <Input
                      value={keyName}
                      onChange={(e) => setKeyName(e.target.value)}
                      placeholder="e.g. Jenkins CI/CD Auditor"
                    />
                  </div>
                  <Button type="submit" disabled={!keyName.trim()} className="w-full">
                    <Plus className="h-4 w-4 mr-2" /> Generate Key
                  </Button>
                </form>

                {newCreatedKey && (
                  <div className="mt-6 bg-warning/10 border border-warning/20 p-4 rounded-lg space-y-3">
                    <p className="text-xs font-semibold text-warning">
                      Make sure to copy this key now. It will not be shown again.
                    </p>
                    <div className="flex items-center gap-2 bg-background p-2.5 rounded border border-white/10">
                      <span className="font-mono text-xs text-foreground break-all select-all flex-1">{newCreatedKey}</span>
                      <button
                        onClick={() => copyToClipboard(newCreatedKey)}
                        className="text-muted hover:text-foreground p-1 hover:bg-white/5 rounded"
                      >
                        <Copy className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Active Keys Column */}
          <div className="space-y-5">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle>Active Client API Keys</CardTitle>
                <button onClick={fetchApiKeys} className="text-muted hover:text-foreground">
                  <RefreshCw className="h-4 w-4" />
                </button>
              </CardHeader>
              <CardContent className="space-y-3">
                {loadingKeys && <div className="text-center p-4 text-muted">Loading API keys...</div>}
                {!loadingKeys && apiKeys.length === 0 && (
                  <div className="text-center p-8 text-muted border border-dashed border-line rounded-lg">
                    No active API keys configured. Provision one on the left for CI/CD integrations.
                  </div>
                )}
                {apiKeys.map((key) => (
                  <div key={key.id} className="flex justify-between items-center bg-elevated border border-line p-4 rounded-lg">
                    <div>
                      <h4 className="font-semibold text-foreground text-sm flex items-center gap-1.5">
                        <Key className="h-4 w-4 text-brand" /> {key.name}
                      </h4>
                      <p className="text-xs text-muted mt-1.5">
                        Created: {new Date(key.created_at).toLocaleDateString()}
                        {key.last_used_at && ` | Last Used: ${new Date(key.last_used_at).toLocaleDateString()}`}
                      </p>
                    </div>
                    <Button size="sm" variant="destructive" onClick={() => handleRevokeApiKey(key.id)}>
                      Revoke
                    </Button>
                  </div>
                ))}
              </CardContent>
            </Card>
          </div>
        </div>
      )}
    </div>
  );
}
