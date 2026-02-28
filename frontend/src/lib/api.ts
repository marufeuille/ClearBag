/**
 * ClearBag API クライアント
 *
 * バックエンド API との通信を担当する。
 * 全リクエストに Firebase ID トークンを自動付与する。
 */

import { getIdToken } from "./firebase";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";

// E2E テスト時は Firebase ID トークン取得をスキップ
const IS_E2E = process.env.NEXT_PUBLIC_E2E === "true";

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly detail: string,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function handleResponse<T>(res: Response, method: string, path: string): Promise<T> {
  if (!res.ok) {
    let detail = "";
    try {
      const body = await res.json();
      detail = body.detail ?? "";
    } catch { /* JSON でない場合は空文字 */ }
    throw new ApiError(res.status, detail, `${method} ${path} failed: ${res.status}`);
  }
  if (res.status === 204) {
    return undefined as unknown as T;
  }
  return res.json() as Promise<T>;
}

export interface DocumentRecord {
  id: string;
  status: "pending" | "processing" | "completed" | "error";
  original_filename: string;
  mime_type: string;
  summary: string;
  category: string;
  error_message: string | null;
}

export interface EventData {
  summary: string;
  start: string;
  end: string;
  location: string;
  description: string;
  confidence: string;
}

export interface TaskData {
  id: string;
  title: string;
  due_date: string;
  assignee: string;
  note: string;
  completed: boolean;
}

export interface UserProfile {
  id: string;
  name: string;
  grade: string;
  keywords: string;
}

export interface Settings {
  plan: "free" | "premium";
  documents_this_month: number;
  ical_url: string;
  notification_web_push: boolean;
}

async function authHeaders(): Promise<Record<string, string>> {
  const token = IS_E2E ? "e2e-test-token" : await getIdToken();
  return {
    Authorization: `Bearer ${token}`,
    "Content-Type": "application/json",
  };
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: await authHeaders(),
  });
  return handleResponse<T>(res, "GET", path);
}

async function post<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: await authHeaders(),
    body: body != null ? JSON.stringify(body) : undefined,
  });
  return handleResponse<T>(res, "POST", path);
}

async function patch<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "PATCH",
    headers: await authHeaders(),
    body: JSON.stringify(body),
  });
  return handleResponse<T>(res, "PATCH", path);
}

async function del(path: string): Promise<void> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "DELETE",
    headers: await authHeaders(),
  });
  await handleResponse<void>(res, "DELETE", path);
}

// ── ドキュメント ──────────────────────────────────────────────────────────────

export async function uploadDocument(
  file: File
): Promise<{ id: string; status: string }> {
  const token = IS_E2E ? "e2e-test-token" : await getIdToken();
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${API_BASE}/api/documents/upload`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: formData,
  });
  return handleResponse<{ id: string; status: string }>(res, "POST", "/api/documents/upload");
}

export const getDocuments = () => get<DocumentRecord[]>("/api/documents");
export const getDocument = (id: string) =>
  get<DocumentRecord>(`/api/documents/${id}`);
export const deleteDocument = (id: string) =>
  del(`/api/documents/${id}`);

// ── イベント ──────────────────────────────────────────────────────────────────

export function getEvents(params?: {
  from?: string;
  to?: string;
  profile_id?: string;
}) {
  const qs = new URLSearchParams();
  if (params?.from) qs.set("from_date", params.from);
  if (params?.to) qs.set("to_date", params.to);
  if (params?.profile_id) qs.set("profile_id", params.profile_id);
  const query = qs.toString() ? `?${qs}` : "";
  return get<EventData[]>(`/api/events${query}`);
}

// ── タスク ────────────────────────────────────────────────────────────────────

export const getTasks = (completed?: boolean) => {
  const qs = completed !== undefined ? `?completed=${completed}` : "";
  return get<TaskData[]>(`/api/tasks${qs}`);
};

export const completeTask = (taskId: string, completed: boolean) =>
  patch<{ completed: boolean }>(`/api/tasks/${taskId}`, { completed });

// ── プロファイル ──────────────────────────────────────────────────────────────

export const getProfiles = () => get<UserProfile[]>("/api/profiles");

export const createProfile = (data: Omit<UserProfile, "id">) =>
  post<UserProfile>("/api/profiles", data);

export const updateProfile = (
  id: string,
  data: Omit<UserProfile, "id">
) =>
  patch<UserProfile>(`/api/profiles/${id}`, data);

export const deleteProfile = (id: string) =>
  del(`/api/profiles/${id}`);

// ── 設定 ──────────────────────────────────────────────────────────────────────

export const getSettings = () => get<Settings>("/api/settings");

export const updateSettings = (data: Partial<Settings>) =>
  patch<Settings>("/api/settings", data);

// ── ファミリー ────────────────────────────────────────────────────────────────

export interface FamilyInfo {
  id: string;
  name: string;
  plan: "free" | "premium";
  documents_this_month: number;
  role: "owner" | "member";
}

export interface FamilyMember {
  uid: string;
  role: "owner" | "member";
  display_name: string;
  email: string;
}

export interface InviteResult {
  invitation_id: string;
  invite_url: string;
}

export interface JoinResult {
  family_id: string;
  name: string;
  role: string;
}

// ── Push サブスクリプション ───────────────────────────────────────────────────

export interface PushSubscriptionKeys {
  auth: string;
  p256dh: string;
}

export async function registerPushSubscription(
  endpoint: string,
  keys: PushSubscriptionKeys,
): Promise<void> {
  await post<void>("/api/push-subscriptions", { endpoint, keys });
}

export async function deletePushSubscription(): Promise<void> {
  await post<void>("/api/push-subscriptions/unsubscribe");
}

// ── ファミリー ────────────────────────────────────────────────────────────────

export const getFamily = () => get<FamilyInfo>("/api/families/me");
export const getFamilyMembers = () => get<FamilyMember[]>("/api/families/members");
export const updateFamilyName = (name: string) => post<FamilyInfo>("/api/families", { name });
export const inviteMember = (email: string) => post<InviteResult>("/api/families/invite", { email });
export const joinFamily = (token: string) => post<JoinResult>("/api/families/join", { token });
export const removeMember = (uid: string) => del(`/api/families/members/${uid}`);
