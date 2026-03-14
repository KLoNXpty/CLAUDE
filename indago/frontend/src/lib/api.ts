/**
 * INDAGO Evidence Capture Platform
 * API Client
 */
import axios from "axios";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export const api = axios.create({
  baseURL: API_BASE,
  headers: {
    "Content-Type": "application/json",
  },
});

// Auth interceptor
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("indago_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem("indago_token");
      window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);

// Auth
export const authApi = {
  login: (username: string, password: string) =>
    api.post("/auth/login", { username, password }),
  register: (data: any) => api.post("/auth/register", data),
  me: () => api.get("/auth/me"),
};

// Captures
export const capturesApi = {
  create: (data: CreateCaptureData) => api.post("/captures", data),
  list: (params?: { skip?: number; limit?: number; status?: string; case_number?: string }) =>
    api.get("/captures", { params }),
  get: (id: number) => api.get(`/captures/${id}`),
  getStatus: (id: number) => api.get(`/captures/${id}/status`),
  getScreenshots: (id: number) => api.get(`/captures/${id}/screenshots`),
  getLogs: (id: number) => api.get(`/captures/${id}/logs`),
  getMetadata: (id: number) => api.get(`/captures/${id}/metadata`),
  getSocial: (id: number) => api.get(`/captures/${id}/social`),
  getHashes: (id: number) => api.get(`/captures/${id}/hashes`),
  verify: (id: number) => api.post(`/captures/${id}/verify`),
  generateReport: (id: number) => api.post(`/captures/${id}/report`),
  download: (id: number) => api.get(`/captures/${id}/download`, { responseType: "blob" }),
  cancel: (id: number) => api.post(`/captures/${id}/cancel`),
  compare: (idA: number, idB: number) =>
    api.post("/captures/compare", { capture_id_a: idA, capture_id_b: idB }),
  createSchedule: (data: any) => api.post("/captures/schedules", data),
  listSchedules: () => api.get("/captures/schedules/list"),
};

export interface CreateCaptureData {
  url: string;
  capture_type?: string;
  case_number?: string;
  case_description?: string;
  options?: Record<string, any>;
}

export interface Capture {
  id: number;
  evidence_id: string;
  url: string;
  final_url?: string;
  domain?: string;
  status: "pending" | "running" | "completed" | "failed" | "cancelled";
  capture_type: string;
  social_platform?: string;
  case_number?: string;
  case_description?: string;
  initiated_at: string;
  capture_started_at?: string;
  capture_completed_at?: string;
  server_ip?: string;
  http_status_code?: number;
  html_sha256?: string;
  dom_sha256?: string;
  package_sha256?: string;
  package_sha512?: string;
  tsa_timestamp?: string;
  tsa_url?: string;
  total_resources: number;
  total_size_bytes: number;
  screenshot_count: number;
  is_locked: boolean;
  error_message?: string;
  progress: number;
}
