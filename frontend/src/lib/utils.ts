import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatPercent(value: number | string | null | undefined) {
  if (value === null || value === undefined) return "-";
  const rawValue = typeof value === "string" ? value.trim() : value;
  if (rawValue === "") return "-";
  const parsed = typeof rawValue === "string"
    ? Number(rawValue.endsWith("%") ? rawValue.slice(0, -1) : rawValue)
    : rawValue;
  if (!Number.isFinite(parsed)) return "-";
  const normalized = typeof rawValue === "string" && rawValue.endsWith("%")
    ? parsed
    : parsed <= 1 ? parsed * 100 : parsed;
  return `${Math.round(normalized)}%`;
}

export function formatDate(value: string | null | undefined) {
  if (!value) return "-";
  return new Date(value).toLocaleString();
}
