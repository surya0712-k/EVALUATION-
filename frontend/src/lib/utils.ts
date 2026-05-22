import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export const API_BASE = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.trim() || "";

/** Fix common .env mistakes, e.g. `http://host:8000/api/auth` or `.../api/auth/google`. */
function normalizeApiBaseOrigin(raw: string): string {
  let b = raw.trim().replace(/\/+$/, "");
  b = b.replace(/\/api\/auth(?:\/.*)?$/i, "");
  return b.replace(/\/+$/, "");
}

/**
 * Join API origin with a path. If `VITE_API_BASE_URL` incorrectly ends with `/api`
 * and the path starts with `/api`, one segment is dropped so we never call
 * `/api/api/...` (that returns 404 "Not Found" on many servers).
 */
export function apiUrl(path: string) {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  if (!API_BASE) return normalizedPath;

  let base = normalizeApiBaseOrigin(API_BASE);
  if (
    (normalizedPath.startsWith("/api/") || normalizedPath === "/api") &&
    base.endsWith("/api")
  ) {
    const rest =
      normalizedPath === "/api" ? "" : normalizedPath.replace(/^\/api/, "") || "";
    return `${base}${rest}`;
  }
  return `${base}${normalizedPath}`;
}

/** Use when HTTP 404 returns generic FastAPI `detail: "Not Found"`. */
export function friendlyApi404(requestUrl: string): string {
  const staleHint =
    requestUrl.includes("auth/google") || requestUrl.includes("/api/auth/")
      ? " If email login hits the API but this URL 404s, port 8000 is often an old server: free the port (Task Manager) and start the API again from this repo (see start_backend.ps1)."
      : "";
  return `No API at ${requestUrl} (404). Set VITE_API_BASE_URL to your FastAPI root (e.g. http://localhost:8000), restart Vite, and run the backend. Or leave VITE_API_BASE_URL empty and use npm run dev so /api is proxied.${staleHint}`;
}

export function formatApiErrorDetail(detail: unknown): string {
  if (detail == null || detail === "") return "";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((e) => {
        if (e && typeof e === "object" && "msg" in e) {
          return String((e as { msg: string }).msg);
        }
        return JSON.stringify(e);
      })
      .join("; ");
  }
  if (typeof detail === "object") return JSON.stringify(detail);
  return String(detail);
}
