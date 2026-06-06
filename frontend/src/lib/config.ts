function readInt(name: string, fallback: number) {
  const raw = process.env[name];
  if (!raw) return fallback;
  const parsed = Number(raw);
  return Number.isFinite(parsed) && parsed > 0 ? Math.floor(parsed) : fallback;
}

export const frontendConfig = {
  apiRequestTimeoutMs: readInt("NEXT_PUBLIC_API_TIMEOUT_MS", 60_000),
  pollIntervalMs: readInt("NEXT_PUBLIC_POLL_INTERVAL_MS", 2000),
  queryGcTimeMs: readInt("NEXT_PUBLIC_QUERY_GC_TIME_MS", 300_000),
  queryStaleTimeMs: readInt("NEXT_PUBLIC_QUERY_STALE_TIME_MS", 60_000),
  maxBulkDocuments: readInt("NEXT_PUBLIC_MAX_BULK_DOCUMENTS", 2000),
};
