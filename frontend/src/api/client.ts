// Minimal typed fetch wrapper around the Trove API.

// Default to same-origin relative requests: the frontend's nginx reverse-proxies
// /api to the backend, so one image works behind any host (TrueNAS, k8s ingress,
// compose) with no baked URL and no CORS. Set VITE_API_BASE_URL only to target a
// different origin (e.g. the Vite dev server calling the backend on :8000).
const BASE_URL = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(
  /\/$/,
  "",
) ?? "";

const TOKEN_KEY = "trove_token";

export function getToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setToken(token: string | null): void {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token);
    else localStorage.removeItem(TOKEN_KEY);
  } catch {
    /* storage unavailable (private mode) */
  }
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

// FastAPI returns `detail` as a string, or a list of validation errors.
export function errorMessage(data: unknown, fallback: string): string {
  if (data && typeof data === "object" && "detail" in data) {
    const detail = (data as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      return detail
        .map((d: { loc?: unknown[]; msg?: string }) => {
          const field = d.loc?.filter((p) => p !== "body").join(".");
          return field ? `${field}: ${d.msg}` : d.msg;
        })
        .join("; ");
    }
  }
  return fallback;
}

function authHeaders(): Record<string, string> {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function handle<T>(resp: Response): Promise<T> {
  if (resp.status === 204) return undefined as T;
  const text = await resp.text();
  let data: unknown = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = null;
  }
  if (!resp.ok) {
    throw new ApiError(resp.status, errorMessage(data, resp.statusText || "Request failed"));
  }
  return data as T;
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const headers = authHeaders();
  if (body !== undefined) headers["Content-Type"] = "application/json";
  const resp = await fetch(`${BASE_URL}${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  return handle<T>(resp);
}

async function upload<T>(path: string, file: File): Promise<T> {
  const form = new FormData();
  form.append("file", file);
  const resp = await fetch(`${BASE_URL}${path}`, {
    method: "PUT",
    headers: authHeaders(),
    body: form,
  });
  return handle<T>(resp);
}

// Fetch a protected file with the bearer token and hand it to the browser.
async function download(path: string, filename: string): Promise<void> {
  const resp = await fetch(`${BASE_URL}${path}`, { headers: authHeaders() });
  if (!resp.ok) await handle(resp);
  const blob = await resp.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 10_000);
}

export const api = {
  get: <T>(path: string) => request<T>("GET", path),
  post: <T>(path: string, body?: unknown) => request<T>("POST", path, body),
  put: <T>(path: string, body?: unknown) => request<T>("PUT", path, body),
  patch: <T>(path: string, body?: unknown) => request<T>("PATCH", path, body),
  del: <T>(path: string) => request<T>("DELETE", path),
  upload,
  download,
  baseUrl: BASE_URL,
};
