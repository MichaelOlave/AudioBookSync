"use client";

import React, { createContext, useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { User } from "@/lib/api/types";
import { login as apiLogin, register as apiRegister, logout as apiLogout, getCurrentUser } from "@/lib/api/auth";
import { apiClient } from "@/lib/api/client";

export interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  loading: boolean;
  error: string | null;
  login: (username: string, password: string) => Promise<void>;
  register: (username: string, email: string, password: string) => Promise<void>;
  logout: () => void;
}

export const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Restore session from API on mount
  useEffect(() => {
    const restoreSession = async () => {
      try {
        // Check if we have valid tokens
        const token = apiClient.getAccessToken();
        if (token && !apiClient.isTokenExpired()) {
          // Token is valid, fetch user data from API
          const userData = await getCurrentUser();
          setUser(userData);
          setError(null);
        } else if (token && apiClient.isRefreshTokenExpired()) {
          // Refresh token expired, clear everything
          apiClient.clearTokens();
          setUser(null);
        }
      } catch {
        setError("Failed to restore session");
        setUser(null);
      } finally {
        setLoading(false);
      }
    };

    restoreSession();
  }, []);

  const login = useCallback(async (username: string, password: string) => {
    setLoading(true);
    setError(null);

    try {
      await apiLogin(username, password);
      // Fetch user data from API after successful login
      const userData = await getCurrentUser();
      setUser(userData);
    } catch (err) {
      const errorMsg =
        err instanceof Error
          ? err.message
          : typeof err === "object" && err !== null && "detail" in err
            ? (err as { detail?: string }).detail || "Login failed"
            : "Login failed";
      setError(errorMsg);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const register = useCallback(
    async (username: string, email: string, password: string) => {
      setLoading(true);
      setError(null);

      try {
        await apiRegister(username, email, password);
        // Registration successful but user is not logged in yet
        // User must login separately
      } catch (err) {
        const errorMsg =
          err instanceof Error
            ? err.message
            : typeof err === "object" && err !== null && "detail" in err
              ? (err as { detail?: string }).detail || "Registration failed"
              : "Registration failed";
        setError(errorMsg);
        throw err;
      } finally {
        setLoading(false);
      }
    },
    []
  );

  const logout = useCallback(() => {
    apiLogout();
    setUser(null);
    setError(null);
    router.push("/login");
  }, [router]);

  const value: AuthContextType = {
    user,
    isAuthenticated: !!user,
    loading,
    error,
    login,
    register,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
