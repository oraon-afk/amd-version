"use client";

import { useRouter } from "next/navigation";
import { createContext, ReactNode, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { getCurrentUser, loginUser, registerUser } from "@/services/auth/auth-service";
import { clearTokens, getAccessToken, setTokens } from "@/services/auth/token-storage";
import { User } from "@/types/api";

type LoginPayload = {
  email: string;
  password: string;
};

type RegisterPayload = {
  email: string;
  password: string;
  full_name?: string;
  company_name?: string;
  role?: string;
};

type AuthContextValue = {
  user: User | null;
  isLoading: boolean;
  login: (payload: LoginPayload) => Promise<User>;
  register: (payload: RegisterPayload) => Promise<void>;
  logout: () => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function loadUser() {
      const token = getAccessToken();
      if (!token) {
        setIsLoading(false);
        return;
      }
      try {
        setUser(await getCurrentUser());
      } catch {
        clearTokens();
        setUser(null);
      } finally {
        setIsLoading(false);
      }
    }
    loadUser();
  }, []);

  const login = useCallback(async (payload: LoginPayload) => {
    const tokens = await loginUser(payload);
    setTokens(tokens.access_token, tokens.refresh_token);
    try {
      const currentUser = await getCurrentUser();
      setUser(currentUser);
      return currentUser;
    } catch (error) {
      clearTokens();
      setUser(null);
      throw error;
    }
  }, []);

  const register = useCallback(async (payload: RegisterPayload) => {
    await registerUser({
      email: payload.email,
      password: payload.password,
      full_name: payload.full_name,
      role: payload.role,
    });
  }, []);

  const logout = useCallback(() => {
    clearTokens();
    setUser(null);
    router.push("/login");
  }, [router]);

  const value = useMemo(
    () => ({ user, isLoading, login, register, logout }),
    [user, isLoading, login, register, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside AuthProvider");
  return context;
}
