export type CommandPreset = {
  id: string;
  i18nKey: string;
  category?: "edit" | "analyze" | "create";
  actionType?: "inline_edit" | "chat_only" | "new_document";
};

export type TextMetrics = {
  clarity: number;
  readability: number;
  formality: number;
  avg_sentence_length: number;
  word_count: number;
};

export type DiffChunk = { kind: string; text: string };

export type EditProposal = {
  original_target: string;
  edited_target: string;
  proposed_full_text: string;
  proposed_html: string;
  selection_start: number;
  selection_end: number;
  diff: DiffChunk[];
  critic: { pass?: boolean; issues?: string[]; retry_prompt?: string };
  metrics_before: TextMetrics;
  metrics_after: TextMetrics;
  fact_claims: { quote: string; reason: string }[];
  command_id: string;
};

export type DocumentRecord = {
  id: number;
  title: string;
  content: string;
  project_id?: number | null;
  chat_id?: number | null;
  source?: string;
  memory?: Record<string, unknown>;
  style_profile?: Record<string, unknown>;
  updated_at?: string;
};

export type ChatRecord = {
  id: number;
  project_id: number;
  title: string;
  updated_at: string;
  pinned?: boolean;
  document_id?: number;
  document_ids?: number[];
};

export type ExportFormat = "txt" | "md" | "html" | "docx" | "pdf";

export type ProjectRecord = {
  id: number;
  title: string;
  memory?: Record<string, unknown>;
  updated_at?: string;
};

export type ChatMessage = {
  id: number;
  role: string;
  content: string;
  metadata?: Record<string, unknown>;
  created_at?: string;
};

export type VersionMeta = {
  id: number;
  label: string;
  command_id: string | null;
  created_at: string;
};

export type AppSettings = {
  ollama_base_url: string;
  ollama_model: string;
  ui_locale: string;
  ollama_connected: boolean;
  ollama_error?: string;
};

export type IntentResult = {
  needs_clarification: boolean;
  question: string;
  interpreted_scope: "selection" | "document" | "create_file";
  command_hint: string;
  action_type: "edit" | "analyze" | "create";
  create_action: string | null;
};

export type ConfirmResult = {
  kind: string;
  command_id?: string;
  proposal?: EditProposal;
  text?: string;
  document_id?: number;
  title?: string;
  content?: string;
};

export function formatApiError(raw: string): string {
  const text = raw.trim();
  if (!text) return raw;
  try {
    const j = JSON.parse(text) as { detail?: unknown };
    const d = j.detail;
    if (typeof d === "string") return d;
    if (Array.isArray(d)) {
      return d.map((x) => (typeof x === "object" && x && "msg" in x ? String((x as { msg: string }).msg) : String(x))).join("; ");
    }
  } catch {
    /* not JSON */
  }
  return text;
}

async function jsonFetch<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });
  if (!res.ok) {
    const text = await res.text();
    let msg = formatApiError(text || res.statusText);
    if (msg === "Internal Server Error" && !text.trim()) {
      msg = `Ошибка сервера (${res.status}). Убедитесь, что бэкенд запущен: cd backend && .venv/bin/uvicorn app.main:app --reload --port 8001`;
    }
    throw new Error(msg);
  }
  return res.json() as Promise<T>;
}

export const api = {
  getSettings: () => jsonFetch<AppSettings>("/api/settings"),
  patchSettings: (body: Partial<AppSettings>) =>
    jsonFetch<AppSettings>("/api/settings", {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
  listCommands: () => jsonFetch<CommandPreset[]>("/api/commands"),
  bootstrap: () => jsonFetch<ChatRecord>("/api/workspace/bootstrap", { method: "POST" }),
  listProjects: () => jsonFetch<ProjectRecord[]>("/api/projects"),
  listChats: (projectId?: number) =>
    jsonFetch<ChatRecord[]>(projectId ? `/api/chats?project_id=${projectId}` : "/api/chats"),
  createChat: (projectId?: number) =>
    jsonFetch<ChatRecord>("/api/chats", {
      method: "POST",
      body: JSON.stringify({ project_id: projectId, title: "New chat" }),
    }),
  getChat: (chatId: number) => jsonFetch<ChatRecord>(`/api/chats/${chatId}`),
  deleteChat: (chatId: number) =>
    jsonFetch<{ ok: boolean }>(`/api/chats/${chatId}`, { method: "DELETE" }),
  patchChat: (chatId: number, patch: { title?: string; pinned?: boolean }) =>
    jsonFetch<ChatRecord>(`/api/chats/${chatId}`, {
      method: "PATCH",
      body: JSON.stringify(patch),
    }),
  downloadDocument: async (docId: number, format: ExportFormat) => {
    const res = await fetch(`/api/documents/${docId}/export?format=${format}`);
    if (!res.ok) {
      const text = await res.text();
      throw new Error(formatApiError(text || res.statusText));
    }
    const blob = await res.blob();
    const dispo = res.headers.get("Content-Disposition") || "";
    const match = /filename="([^"]+)"/.exec(dispo);
    const filename = match?.[1] || `document.${format}`;
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  },
  listMessages: (chatId: number) => jsonFetch<ChatMessage[]>(`/api/chats/${chatId}/messages`),
  listDocuments: (projectId?: number) =>
    jsonFetch<DocumentRecord[]>(
      projectId ? `/api/documents?project_id=${projectId}` : "/api/documents",
    ),
  getDocument: (id: number) => jsonFetch<DocumentRecord>(`/api/documents/${id}`),
  updateDocument: (id: number, patch: { title?: string; content?: string }) =>
    jsonFetch<DocumentRecord>(`/api/documents/${id}`, {
      method: "PATCH",
      body: JSON.stringify(patch),
    }),
  listVersions: (id: number) => jsonFetch<VersionMeta[]>(`/api/documents/${id}/versions`),
  restoreVersion: (docId: number, versionId: number) =>
    jsonFetch<{ content: string }>(`/api/documents/${docId}/restore/${versionId}`, {
      method: "POST",
    }),
  importFile: async (docId: number, file: File) => {
    const form = new FormData();
    form.append("file", file);
    const res = await fetch(`/api/documents/${docId}/import`, { method: "POST", body: form });
    if (!res.ok) throw new Error(await res.text());
    return res.json() as Promise<{ content: string }>;
  },
  proposeEdit: (docId: number, body: Record<string, unknown>) =>
    jsonFetch<EditProposal>(`/api/documents/${docId}/edit`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  acceptEdit: (
    docId: number,
    body: {
      proposed_full_text: string;
      command_id: string;
      custom_instruction?: string;
      label?: string;
    },
  ) =>
    jsonFetch<{ content: string; memory?: Record<string, unknown> }>(
      `/api/documents/${docId}/accept`,
      { method: "POST", body: JSON.stringify(body) },
    ),
  agentIntent: (body: Record<string, unknown>) =>
    jsonFetch<IntentResult>("/api/agent/intent", { method: "POST", body: JSON.stringify(body) }),
  agentConfirm: (body: Record<string, unknown>) =>
    jsonFetch<ConfirmResult>("/api/agent/confirm", { method: "POST", body: JSON.stringify(body) }),
  generateDocument: (body: Record<string, unknown>) =>
    jsonFetch<ConfirmResult>("/api/documents/generate", {
      method: "POST",
      body: JSON.stringify(body),
    }),
};

export function htmlToPlain(html: string): string {
  const div = document.createElement("div");
  div.innerHTML = html;
  return (div.innerText || div.textContent || "").replace(/\u00a0/g, " ");
}

export function isEmptyHtml(html: string): boolean {
  return htmlToPlain(html).trim().length === 0;
}
