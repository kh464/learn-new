const ADMIN_HEADER = "X-Admin-Key";

export function buildHeaders(adminKey, extraHeaders = {}) {
  const headers = new Headers(extraHeaders);
  const normalized = String(adminKey || "").trim();
  if (normalized) {
    headers.set(ADMIN_HEADER, normalized);
  }
  return headers;
}

export async function requestJson(path, adminKey, options = {}) {
  const requestOptions = { ...options, headers: buildHeaders(adminKey, options.headers) };
  const response = await fetch(path, requestOptions);
  if (!response.ok) {
    throw new Error(`${path} -> ${response.status} ${await response.text()}`.trim());
  }
  return response.json();
}

export async function requestText(path, adminKey, options = {}) {
  const requestOptions = { ...options, headers: buildHeaders(adminKey, options.headers) };
  const response = await fetch(path, requestOptions);
  if (!response.ok) {
    throw new Error(`${path} -> ${response.status} ${await response.text()}`.trim());
  }
  return response.text();
}

export function createTaskSocket(taskId, adminKey, handlers = {}) {
  const base = `${window.location.protocol === "https:" ? "wss" : "ws"}://${window.location.host}/ws/tasks/${taskId}`;
  const url = String(adminKey || "").trim()
    ? `${base}?api_key=${encodeURIComponent(String(adminKey).trim())}`
    : base;
  const socket = new WebSocket(url);
  if (handlers.message) {
    socket.addEventListener("message", handlers.message);
  }
  if (handlers.error) {
    socket.addEventListener("error", handlers.error);
  }
  if (handlers.close) {
    socket.addEventListener("close", handlers.close);
  }
  return socket;
}

export const apiPaths = {
  sessions: "/api/sessions",
  taskTurns: "/api/tasks/turns",
  deadLetter: "/api/tasks/dead-letter",
  runtimeSummary: "/api/runtime/summary",
};
