import axios from "axios";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const TOKEN_KEY = "sva_token";
const USER_KEY = "sva_user";

const api = axios.create({ baseURL: API_BASE_URL });

// --- token ---------------------------------------------------------------
export function getToken() {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function getStoredUser() {
  try {
    const raw = localStorage.getItem(USER_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

function simpanSesi(token, user) {
  try {
    localStorage.setItem(TOKEN_KEY, token);
    localStorage.setItem(USER_KEY, JSON.stringify(user));
  } catch {
    // localStorage bisa diblokir (private mode); sesi tetap jalan sampai reload.
  }
}

export function logout() {
  try {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  } catch {
    // abaikan
  }
}

// Sisipkan token pada setiap request.
api.interceptors.request.use((config) => {
  const token = getToken();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Token kedaluwarsa/ditolak → bersihkan sesi supaya UI kembali ke layar login.
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err?.response?.status === 401) {
      logout();
      window.dispatchEvent(new Event("sva-unauthorized"));
    }
    return Promise.reject(err);
  }
);

// --- auth ----------------------------------------------------------------
export async function login(username, password) {
  // Endpoint /auth/login memakai OAuth2 password flow (form-urlencoded).
  const form = new URLSearchParams();
  form.append("username", username);
  form.append("password", password);

  const { data } = await api.post("/auth/login", form, {
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
  });

  const user = { username: data.username, role: data.role };
  simpanSesi(data.access_token, user);
  return user;
}

// --- chat ----------------------------------------------------------------
export async function sendChatMessage(sessionId, message, imageId = null) {
  const payload = { session_id: sessionId, message };
  if (imageId) payload.image_id = imageId;
  const { data } = await api.post("/chat", payload);
  return data;
}

export async function getChatHistory(sessionId) {
  const { data } = await api.get("/chat/history", { params: { session_id: sessionId } });
  return data;
}

export async function uploadFile(file) {
  const formData = new FormData();
  formData.append("file", file);
  const { data } = await api.post("/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function addDocument(filename, content) {
  const { data } = await api.post("/documents", { filename, content });
  return data;
}

export default api;
