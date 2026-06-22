/**
 * Constants shared between the frontend and backend data model.
 * Edge colors/styles and risk tier definitions.
 */

// ─── Edge color/style map ─────────────────────────────────────────────
export const EDGE_STYLES = {
  transaction:      { color: '#3b82f6', width: 2, dash: null,          label: 'Transaction' },
  ownership:        { color: '#8b5cf6', width: 2, dash: null,          label: 'Ownership' },
  shared_address:   { color: '#f59e0b', width: 1, dash: [4, 3],        label: 'Shared Address' },
  shared_phone:     { color: '#ef4444', width: 1, dash: [4, 3],        label: 'Shared Phone' },
  shared_email:     { color: '#ec4899', width: 1, dash: [4, 3],        label: 'Shared Email' },
  shared_ip:        { color: '#14b8a6', width: 1, dash: [4, 3],        label: 'Shared IP' },
  shared_device:    { color: '#f97316', width: 1, dash: [4, 3],        label: 'Shared Device' },
  llm_discovered:   { color: '#a855f7', width: 2, dash: [6, 4],        label: 'LLM Discovered' },
};

// ─── Node color by risk tier ──────────────────────────────────────────
export const RISK_COLORS = {
  low:    { color: '#22c55e', bg: '#dcfce7', label: 'Low (0-29)' },
  medium: { color: '#f59e0b', bg: '#fef3c7', label: 'Medium (30-69)' },
  high:   { color: '#ef4444', bg: '#fee2e2', label: 'High (70-100)' },
};

export function riskTier(score) {
  if (score == null) return 'low';
  if (score >= 70) return 'high';
  if (score >= 30) return 'medium';
  return 'low';
}
