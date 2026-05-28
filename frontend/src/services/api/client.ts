"use client";

import axios, { AxiosError } from "axios";
import { clearTokens, getAccessToken } from "@/services/auth/token-storage";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "/api/backend";

export type NormalizedApiError = {
  message: string;
  status?: number;
  code?: string;
};

type ApiErrorResponse = {
  detail?: string | Array<{ msg?: string; message?: string }>;
  message?: string;
  error?: string | { message?: string; code?: string };
};

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60_000,
});

apiClient.interceptors.request.use((config) => {
  const token = getAccessToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError<ApiErrorResponse>) => {
    if (error.response?.status === 401) {
      clearTokens();
    }
    const responseError = error.response?.data?.error;
    const normalized: NormalizedApiError = {
      status: error.response?.status,
      code: typeof responseError === "object" ? responseError?.code : undefined,
      message:
        normalizeError(responseError) ||
        normalizeDetail(error.response?.data?.detail) ||
        error.response?.data?.message ||
        error.message ||
        "Request failed",
    };
    return Promise.reject(normalized);
  },
);

export function getErrorMessage(error: unknown) {
  if (typeof error === "string") return error;
  if (typeof error === "object" && error && "message" in error) {
    return String((error as { message: string }).message);
  }
  return "Something went wrong";
}

function normalizeError(error: ApiErrorResponse["error"]) {
  if (!error) return undefined;
  if (typeof error === "string") return error;
  return error.message;
}

function normalizeDetail(detail: string | Array<{ msg?: string; message?: string }> | undefined) {
  if (!detail) return undefined;
  if (typeof detail === "string") return detail;
  return detail.map((item) => item.msg || item.message).filter(Boolean).join(", ");
}
