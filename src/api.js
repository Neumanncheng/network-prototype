/**
 * Centralized API client — all backend calls go through here.
 * Handles JWT auth automatically.
 *
 * API URL priority:
 *   1. VITE_API_URL env var (set at build time for production)
 *   2. Auto-detect for local dev
 */

const API_BASE = import.meta.env.VITE_API_URL || (() => {
  const host = window.location.hostname;
  if (host === 'localhost' || host === '127.0.0.1') return `http://${host}:8000/api`;
  // Production: backend served from same domain via reverse proxy, or subdomain
  return `https://${host}/api`;
})();

let _token = localStorage.getItem('na_token') || null;

export function getToken() { return _token; }

async function fetchJSON(url, options = {}) {
  const headers = { 'Accept': 'application/json', ...options.headers };
  if (_token) headers['Authorization'] = `Bearer ${_token}`;

  const res = await fetch(`${API_BASE}${url}`, { headers, ...options });

  if (res.status === 401 && _token) {
    // Token expired — clear and let the app redirect to login
    localStorage.removeItem('na_token');
    _token = null;
    window.location.hash = '#login';
    throw new Error('401');
  }

  if (!res.ok) {
    if (res.status === 401) throw new Error('401');
    const body = await res.text().catch(() => '');
    throw new Error(`API ${res.status}: ${body || res.statusText}`);
  }
  return res.json();
}

export const api = {
  // ── Auth ─────────────────────────────────────────
  login: async (username, password) => {
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    });
    if (!res.ok) {
      if (res.status === 401) throw new Error('401');
      throw new Error(await res.text().catch(() => 'Login failed'));
    }
    return res.json();
  },
  setToken: (token) => {
    _token = token;
    localStorage.setItem('na_token', token);
  },
  logout: () => {
    _token = null;
    localStorage.removeItem('na_token');
  },
  isAuthenticated: () => !!_token,

  // ── Graph ────────────────────────────────────────
  getGraph: () => fetchJSON('/graph'),
  getStats: () => fetchJSON('/stats'),
  getNode: (id) => fetchJSON(`/graph/node/${id}`),
  getNeighborhood: (id, depth = 1) => fetchJSON(`/graph/node/${id}/neighborhood?depth=${depth}`),
  listNodes: (type) => fetchJSON(`/graph/nodes${type ? `?type=${type}` : ''}`),

  // ── Analytics ────────────────────────────────────
  getCentrality: (topK = 0) => fetchJSON(`/analytics/centrality${topK > 0 ? `?top_k=${topK}` : ''}`),
  getTopCentral: (metric = 'pagerank', k = 5) => fetchJSON(`/analytics/centrality/top?metric=${metric}&k=${k}`),
  getCommunities: () => fetchJSON('/analytics/communities'),
  getPatterns: () => fetchJSON('/analytics/patterns'),
  findPath: (source, target, maxDepth = 4) =>
    fetchJSON(`/analytics/path?source=${source}&target=${target}&max_depth=${maxDepth}`),
  getTemporal: () => fetchJSON('/analytics/temporal'),

  // ── Risk ─────────────────────────────────────────
  getRiskBreakdown: (nodeId) => fetchJSON(`/risk/${nodeId}`),
  propagateRisk: (fromId, depth = 3) =>
    fetchJSON(`/risk/propagate?from_id=${fromId}&depth=${depth}`),

  // ── LLM ──────────────────────────────────────────
  explainNode: (nodeId) => fetchJSON(`/risk/llm/explain/${nodeId}`),
  explainPath: (source, target) =>
    fetchJSON(`/risk/llm/explain-path?source=${source}&target=${target}`),

  // ── Health ───────────────────────────────────────
  health: () => fetchJSON('/health'),
};
