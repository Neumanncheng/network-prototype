import React, { useState, useEffect } from 'react';
import { api } from '../api.js';
import { RISK_COLORS, riskTier } from '../data/sampleGraph.js';
import './RiskScorePanel.css';

const WEIGHT_LABELS = {
  centrality: 'Centrality',
  community: 'Community Risk',
  pattern: 'Pattern Risk',
  temporal: 'Temporal Risk',
  propagated: 'Propagated Risk',
};

export default function RiskScorePanel({ nodeId }) {
  const [riskData, setRiskData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!nodeId) return;
    let cancelled = false;
    setLoading(true);
    setError(null);

    api.getRiskBreakdown(nodeId)
      .then((data) => { if (!cancelled) setRiskData(data); })
      .catch((err) => { if (!cancelled) setError(err.message); })
      .finally(() => { if (!cancelled) setLoading(false); });

    return () => { cancelled = true; };
  }, [nodeId]);

  if (loading) {
    return (
      <div className="sidebar-section risk-panel">
        <h3>📊 Risk Score Breakdown</h3>
        <div className="rp-loading">Loading risk data...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="sidebar-section risk-panel">
        <h3>📊 Risk Score Breakdown</h3>
        <div className="rp-error">⚠️ {error}</div>
      </div>
    );
  }

  if (!riskData) {
    return (
      <div className="sidebar-section risk-panel">
        <h3>📊 Risk Score Breakdown</h3>
        <div className="rp-empty">No risk data available for this node.</div>
      </div>
    );
  }

  const tier = riskTier(riskData.composite_score);
  const tierInfo = RISK_COLORS[tier] || RISK_COLORS.low;
  const components = riskData.components || {};

  return (
    <div className="sidebar-section risk-panel">
      <h3>📊 Risk Score Breakdown</h3>

      {/* Gauge */}
      <div className="rp-gauge-wrap">
        <svg viewBox="0 0 120 68" className="rp-gauge">
          <path d="M 10 60 A 50 50 0 0 1 110 60" fill="none" stroke="#1e293b" strokeWidth="10" strokeLinecap="round" />
          <path
            d="M 10 60 A 50 50 0 0 1 110 60"
            fill="none"
            stroke={tierInfo.color}
            strokeWidth="10"
            strokeLinecap="round"
            strokeDasharray={`${riskData.composite_score * 0.785} 157`}
          />
          <text x="60" y="42" textAnchor="middle" fill={tierInfo.color} fontSize="22" fontWeight="bold">
            {riskData.composite_score}
          </text>
          <text x="60" y="54" textAnchor="middle" fill="#64748b" fontSize="8">
            NETWORK SCORE
          </text>
        </svg>
      </div>

      {/* Component bars */}
      <div className="rp-components">
        {Object.entries(components).map(([key, comp]) => {
          const label = WEIGHT_LABELS[key] || key;
          const colorMap = {
            centrality: '#3b82f6',
            community: '#8b5cf6',
            pattern: '#f59e0b',
            temporal: '#14b8a6',
            propagated: '#ef4444',
          };
          return (
            <div key={key} className="rp-bar-row">
              <div className="rp-bar-label">
                <span>{label}</span>
                <span className="rp-bar-weight">{Math.round(comp.weight * 100)}%</span>
              </div>
              <div className="rp-bar-track">
                <div
                  className="rp-bar-fill"
                  style={{ width: `${comp.score}%`, background: colorMap[key] || '#64748b' }}
                />
              </div>
              <span className="rp-bar-value">{Math.round(comp.score)}</span>
            </div>
          );
        })}
      </div>

      {/* Formula */}
      <div className="rp-formula">
        <div className="rp-formula-line">Score = Σ (Component × Weight)</div>
        <div className="rp-formula-line">
          Centrality 20% · Community 30% · Pattern 25% · Temporal 15% · Propagated 10%
        </div>
      </div>
    </div>
  );
}
