import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { api } from '../api.js';
import { RISK_COLORS, riskTier } from '../data/sampleGraph.js';
import './NodeDetail.css';

export default function NodeDetail({ node, onClose }) {
  const [explanation, setExplanation] = useState(null);
  const [explaining, setExplaining] = useState(false);

  if (!node) return null;

  const tier = riskTier(node.riskScore);
  const tierInfo = RISK_COLORS[tier] || RISK_COLORS.low;

  const typeIcon = { customer: '👤', account: '🏦', external: '🏢', ip: '🌐', device: '📱' };
  const typeLabel = { customer: 'Customer', account: 'Bank Account', external: 'External Entity', ip: 'IP Address', device: 'Device' };

  // Summarize connected entities from node data
  const connByType = {};
  if (node.connections) {
    for (const c of node.connections) {
      connByType[c.type] = (connByType[c.type] || 0) + 1;
    }
  }

  const edgeTypeCounts = {};
  if (node.edgeDetails) {
    for (const e of node.edgeDetails) {
      edgeTypeCounts[e.type] = (edgeTypeCounts[e.type] || 0) + 1;
    }
  }

  const handleExplain = async () => {
    setExplaining(true);
    try {
      const res = await api.explainNode(node.id);
      setExplanation(res);
    } catch (err) {
      setExplanation({ narrative: `⚠️ Error: ${err.message}` });
    } finally {
      setExplaining(false);
    }
  };

  return (
    <div className="sidebar-section node-detail">
      {/* Header */}
      <div className="nd-header">
        <div className="nd-title-row">
          <span className="nd-icon">{typeIcon[node.type] || '📄'}</span>
          <div>
            <div className="nd-name">{node.label}</div>
            {node.labelZh && <div className="nd-name-zh">{node.labelZh}</div>}
            <div className="nd-type-badge">{typeLabel[node.type] || node.type}</div>
          </div>
          <button className="nd-close" onClick={onClose}>✕</button>
        </div>
      </div>

      {/* Risk bar */}
      <div className="nd-risk-row">
        <div className="nd-risk-bar">
          <div
            className="nd-risk-fill"
            style={{
              width: `${node.riskScore || 0}%`,
              background: tierInfo.color,
            }}
          />
        </div>
        <span className="nd-risk-label" style={{ color: tierInfo.color }}>
          {node.riskScore ?? 'N/A'} · {tierInfo.label}
        </span>
      </div>

      {/* Attributes */}
      <table className="nd-table">
        <tbody>
          {node.country && <tr><td className="nd-key">Country</td><td className="nd-val">{node.country}</td></tr>}
          {node.bank && <tr><td className="nd-key">Bank</td><td className="nd-val">{node.bank}</td></tr>}
          {node.idType && <tr><td className="nd-key">ID Type</td><td className="nd-val">{node.idType}</td></tr>}
          {node.idNumber && <tr><td className="nd-key">ID Number</td><td className="nd-val nd-mono">{node.idNumber}</td></tr>}
          {node.geo && <tr><td className="nd-key">Geo</td><td className="nd-val">{node.geo}</td></tr>}
          {node.isp && <tr><td className="nd-key">ISP</td><td className="nd-val">{node.isp}</td></tr>}
          {node.os && <tr><td className="nd-key">OS</td><td className="nd-val">{node.os}</td></tr>}
        </tbody>
      </table>

      {/* Connected entities */}
      {Object.keys(connByType).length > 0 && (
        <div className="nd-connections">
          <div className="nd-subtitle">🔗 Connected Entities</div>
          <div className="conn-chips">
            {Object.entries(connByType).map(([type, count]) => (
              <span key={type} className="conn-chip">
                {typeIcon[type] || '📄'} {typeLabel[type] || type} <strong>×{count}</strong>
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Edge details */}
      {node.edgeDetails && node.edgeDetails.length > 0 && (
        <div className="nd-edges">
          <div className="nd-subtitle">📋 Relationship Details</div>
          <div className="edge-list">
            {node.edgeDetails.slice(0, 8).map((e) => (
              <div key={e.id} className="edge-item">
                <span className="edge-type-tag">{e.type.replace('_', ' ')}</span>
                {e.amount && <span className="edge-meta">{e.currency} ${Number(e.amount).toLocaleString()}</span>}
                {e.percentage && <span className="edge-meta">{e.percentage}% ownership</span>}
                {e.date && <span className="edge-meta">{e.date}</span>}
                {e.confidence && <span className="edge-meta">confidence: {Math.round(e.confidence * 100)}%</span>}
                {e.evidence && <div className="edge-evidence">"{e.evidence}"</div>}
              </div>
            ))}
            {node.edgeDetails.length > 8 && (
              <div className="edge-more">+{node.edgeDetails.length - 8} more relationships</div>
            )}
          </div>
        </div>
      )}

      {/* ── LLM Explain button ──────────────────────── */}
      <div className="nd-explain-section">
        <button
          className="nd-explain-btn"
          onClick={handleExplain}
          disabled={explaining}
        >
          {explaining ? '⏳ Analysing...' : '🤖 Explain with LLM'}
        </button>

        {explanation && (
          <div className="nd-explain-result">
            {/* Typology badge */}
            {explanation.typology && explanation.typology !== 'Standard pattern — no immediate typology match' && (
              <div className="nd-typology-badge">
                🔍 {explanation.typology}
              </div>
            )}

            {/* Narrative */}
            <div className="nd-explain-text">
              <ReactMarkdown>
                {explanation.narrative || ''}
              </ReactMarkdown>
            </div>

            {/* Risk Factors */}
            {explanation.risk_factors && explanation.risk_factors.length > 0 && (
              <div className="nd-explain-block">
                <div className="nd-block-title">🚩 Risk Factors</div>
                <ul className="nd-block-list">
                  {explanation.risk_factors.map((f, i) => (
                    <li key={i}>{f}</li>
                  ))}
                </ul>
              </div>
            )}

            {/* Investigation Notes */}
            {explanation.investigation_notes && explanation.investigation_notes.length > 0 && (
              <div className="nd-explain-block">
                <div className="nd-block-title">🔎 Investigation Notes</div>
                <ul className="nd-block-list">
                  {explanation.investigation_notes.map((n, i) => (
                    <li key={i}>{n}</li>
                  ))}
                </ul>
              </div>
            )}

            {/* Provider tag */}
            {explanation.llm_provider && explanation.llm_provider !== 'mock' && (
              <div className="nd-provider-tag">
                Powered by {explanation.llm_provider}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
