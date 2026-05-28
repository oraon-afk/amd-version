import { apiClient } from "@/services/api/client";
import { TokenResponse, User } from "@/types/api";

export type RegisterPayload = {
  email: string;
  password: string;
  full_name?: string;
  company_name?: string;
  role?: string;
};

export type LoginPayload = {
  email: string;
  password: string;
};

export async function registerUser(payload: RegisterPayload) {
  const { data } = await apiClient.post<User>("/auth/register", {
    email: payload.email,
    password: payload.password,
    full_name: payload.full_name,
    role: payload.role,
  });
  return data;
}

export async function loginUser(payload: LoginPayload) {
  const { data } = await apiClient.post<TokenResponse>("/auth/login", payload);
  return data;
}

export async function getCurrentUser() {
  const { data } = await apiClient.get<User>("/auth/me");
  return data;
}
