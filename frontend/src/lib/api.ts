import type {
  Job, Project, ProjectDetail, QueueJobResponse,
  StylePreset, TokenResponse, UsageSummary,
} from "./types";

const API = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export const apiBase = API;

// ---------------------------------------------------------------------------
// Invisible auth — a guest token is auto-managed, never exposed to the UI.
// ---------------------------------------------------------------------------

const GUEST_KEY = "animbolt_token";
const GUEST_EMAIL_KEY = "animbolt_guest_email";
const GUEST_PASS = "animbolt-guest-pass-v1";

function isTokenExpired(token: string): boolean {
  try {
    const payload = JSON.parse(atob(token.split(".")[1]));
    return payload.exp < Date.now() / 1000 + 60;
  } catch {
    return true;
  }
}

function newGuestEmail(): string {
  return `guest_${Math.random().toString(36).slice(2, 10)}@animbolt.local`;
}

async function _register(email: string): Promise<TokenResponse> {
  const res = await fetch(`${API}/api/v1/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password: GUEST_PASS }),
  });
  if (!res.ok) throw new Error(`register ${res.status}`);
  return res.json() as Promise<TokenResponse>;
}

async function _login(email: string): Promise<TokenResponse> {
  const res = await fetch(`${API}/api/v1/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password: GUEST_PASS }),
  });
  if (!res.ok) throw new Error(`login ${res.status}`);
  return res.json() as Promise<TokenResponse>;
}

async function tryAuth(email: string): Promise<string | null> {
  try { return (await _register(email)).access_token; } catch { /* fall through */ }
  try { return (await _login(email)).access_token; } catch { /* fall through */ }
  return null;
}

let _inflightToken: Promise<string> | null = null;

async function getToken(): Promise<string> {
  if (typeof window === "undefined") return "";

  const cached = localStorage.getItem(GUEST_KEY);
  if (cached && !isTokenExpired(cached)) return cached;

  // Deduplicate concurrent calls
  if (_inflightToken) return _inflightToken;

  _inflightToken = (async () => {
    localStorage.removeItem(GUEST_KEY);

    // Try stored email first
    const storedEmail = localStorage.getItem(GUEST_EMAIL_KEY) ?? newGuestEmail();
    localStorage.setItem(GUEST_EMAIL_KEY, storedEmail);
    let token = await tryAuth(storedEmail);

    // If that fails, mint a completely fresh identity
    if (!token) {
      const freshEmail = newGuestEmail();
      localStorage.setItem(GUEST_EMAIL_KEY, freshEmail);
      token = await tryAuth(freshEmail);
    }

    if (!token) throw new Error("Auth unavailable — is the backend running?");
    localStorage.setItem(GUEST_KEY, token);
    return token;
  })().finally(() => { _inflightToken = null; });

  return _inflightToken;
}

// ---------------------------------------------------------------------------
// Core fetch wrapper — auth is automatic
// ---------------------------------------------------------------------------

async function req<T>(
  path: string,
  method: string,
  body?: unknown,
  formData = false,
): Promise<T> {
  const token = await getToken();
  const headers: Record<string, string> = {};
  if (token) headers.Authorization = `Bearer ${token}`;
  if (!formData) headers["Content-Type"] = "application/json";

  const res = await fetch(`${API}${path}`, {
    method,
    headers,
    body: body ? (formData ? (body as FormData) : JSON.stringify(body)) : undefined,
  });

  if (res.status === 401) {
    // Token rejected — clear and let next call retry
    if (typeof window !== "undefined") {
      localStorage.removeItem(GUEST_KEY);
      localStorage.removeItem(GUEST_EMAIL_KEY);
    }
    throw Object.assign(new Error("Unauthorized"), { status: 401 });
  }

  if (!res.ok) {
    const j = await res.json().catch(() => ({}));
    throw new Error(String((j as Record<string, unknown>).detail ?? `Request failed: ${res.status}`));
  }
  if (res.status === 204 || res.headers.get("content-length") === "0") {
    return undefined as T;
  }
  return res.json() as Promise<T>;
}

// ---------------------------------------------------------------------------
// Project endpoints
// ---------------------------------------------------------------------------

export const listProjects = () =>
  req<Project[]>("/api/v1/projects", "GET");

export const createProject = (title: string, description: string) =>
  req<Project>("/api/v1/projects", "POST", { title, description });

export const getProject = (projectId: string) =>
  req<ProjectDetail>(`/api/v1/projects/${projectId}`, "GET");

// ---------------------------------------------------------------------------
// Scene endpoints
// ---------------------------------------------------------------------------

export const generateScene = (payload: {
  project_id: string;
  prompt: string;
  style_preset: string;
  max_duration_sec: number;
  aspect_ratio: string;
  llm_provider?: string;
}) =>
  req<{
    scene_id: string;
    scene_version_id: string;
    preview_job_id: string;
    validation_status: string;
  }>("/api/v1/scenes/generate", "POST", payload);

export const regenerateScene = (
  sceneId: string,
  payload: {
    prompt: string;
    style_preset: string;
    max_duration_sec: number;
    aspect_ratio: string;
  },
) =>
  req<{
    scene_id: string;
    scene_version_id: string;
    preview_job_id: string;
    validation_status: string;
  }>(`/api/v1/scenes/${sceneId}/regenerate`, "POST", payload);

export const refineScene = (
  sceneId: string,
  feedback: string,
  llmProvider?: string,
) =>
  req<{
    scene_id: string;
    scene_version_id: string;
    preview_job_id: string;
    validation_status: string;
  }>(`/api/v1/scenes/${sceneId}/refine`, "POST", {
    feedback,
    llm_provider: llmProvider ?? null,
  });

export const renderHD = (sceneId: string) =>
  req<QueueJobResponse>(`/api/v1/scenes/${sceneId}/render-hd`, "POST");

export const listPresets = () =>
  req<StylePreset[]>("/api/v1/scenes/presets", "GET");

// ---------------------------------------------------------------------------
// Job endpoints
// ---------------------------------------------------------------------------

export const getJob = (jobId: string) =>
  req<Job>(`/api/v1/jobs/${jobId}`, "GET");

// ---------------------------------------------------------------------------
// Voiceover endpoints
// ---------------------------------------------------------------------------

export const generateTTS = (payload: { project_id: string; text: string; voice: string }) =>
  req<{ asset_id: string; storage_path: string; mime_type: string; duration_ms: number }>(
    "/api/v1/voiceovers/tts",
    "POST",
    payload,
  );

export const uploadVoiceover = (projectId: string, file: File) => {
  const fd = new FormData();
  fd.append("file", file);
  return req<{ asset_id: string; storage_path: string; mime_type: string; duration_ms: number }>(
    `/api/v1/voiceovers/upload?project_id=${projectId}`,
    "POST",
    fd,
    true,
  );
};

// ---------------------------------------------------------------------------
// Composition endpoints
// ---------------------------------------------------------------------------

export const exportComposition = (projectId: string, title = "Main Composition") =>
  req<QueueJobResponse>(`/api/v1/compositions/${projectId}/export`, "POST", { title });

// ---------------------------------------------------------------------------
// Usage
// ---------------------------------------------------------------------------

export const getUsage = () =>
  req<UsageSummary>("/api/v1/usage", "GET");

export const deleteProject = (projectId: string) =>
  req<void>(`/api/v1/projects/${projectId}`, "DELETE");

export const reorderScenes = (projectId: string, sceneIds: string[]) =>
  req<ProjectDetail>(`/api/v1/projects/${projectId}/reorder-scenes`, "PUT", {
    scene_ids: sceneIds,
  });

export interface StoredChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  created_at: string;
}

export const getChatMessages = (projectId: string) =>
  req<StoredChatMessage[]>(`/api/v1/projects/${projectId}/chat`, "GET");

export const addChatMessage = (projectId: string, role: "user" | "assistant", content: string) =>
  req<StoredChatMessage>(`/api/v1/projects/${projectId}/chat`, "POST", { role, content });
