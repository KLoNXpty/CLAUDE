/**
 * INDAGO Evidence Capture Platform
 * Global State Management (Zustand)
 */
import { create } from "zustand";
import { persist } from "zustand/middleware";

interface User {
  id: number;
  username: string;
  full_name: string;
  email: string;
  role: string;
  organization?: string;
}

interface AuthState {
  token: string | null;
  user: User | null;
  isAuthenticated: boolean;
  setAuth: (token: string, user: User) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      user: null,
      isAuthenticated: false,
      setAuth: (token, user) => {
        localStorage.setItem("indago_token", token);
        set({ token, user, isAuthenticated: true });
      },
      logout: () => {
        localStorage.removeItem("indago_token");
        set({ token: null, user: null, isAuthenticated: false });
      },
    }),
    {
      name: "indago-auth",
    }
  )
);
