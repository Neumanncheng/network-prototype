import React from 'react';
import { EDGE_STYLES } from '../data/sampleGraph.js';
import './EdgeDetail.css';

export default function EdgeDetail({ edge, onClose }) {
  if (!edge) return null;

  const st = EDGE_STYLES[edge.type] || {};
  const typeLabel = st.label || edge.type?.replace('_', ' ') || 'Relationship';

  const fields = [
    { label: 'Type', value: typeLabel, color: st.color },
    { label: 'From', value: edge.sourceLabel },
    { label: 'To', value: edge.targetLabel },
  ];

  if (edge.amount) fields.push({ label: 'Amount', value: `${edge.currency || ''} $${Number(edge.amount).toLocaleString()}` });
  if (edge.date) fields.push({ label: 'Date', value: edge.date });
  if (edge.percentage) fields.push({ label: 'Ownership', value: `${edge.percentage}%` });
  if (edge.ip) fields.push({ label: 'Shared IP', value: edge.ip });
  if (edge.confidence) fields.push({ label: 'Confidence', value: `${Math.round(edge.confidence * 100)}%` });

  return (
    <div className="sidebar-section edge-detail">
      <div className="ed-header">
        <div className="ed-title-row">
          <div className="ed-icon-wrap" style={{ borderColor: st.color || '#475569' }}>
            <span className="ed-line" style={{ background: st.color || '#475569', borderTopStyle: st.dash ? 'dashed' : 'solid' }} />
          </div>
          <div className="ed-title-text">
            <div className="ed-title">{typeLabel}</div>
            <div className="ed-subtitle">Relationship Detail</div>
          </div>
          <button className="ed-close" onClick={onClose}>✕</button>
        </div>
      </div>

      <div className="ed-connection">
        <div className="ed-conn-node">
          <span className="ed-conn-label">{edge.sourceLabel}</span>
          <span className="ed-conn-type">{edge.sourceType}</span>
        </div>
        <div className="ed-conn-arrow" style={{ color: st.color }}>──→</div>
        <div className="ed-conn-node">
          <span className="ed-conn-label">{edge.targetLabel}</span>
          <span className="ed-conn-type">{edge.targetType}</span>
        </div>
      </div>

      <table className="ed-table">
        <tbody>
          {fields.map((f, i) => (
            <tr key={i}>
              <td className="ed-key">{f.label}</td>
              <td className="ed-val" style={f.color ? { color: f.color } : {}}>{f.value}</td>
            </tr>
          ))}
          {edge.evidence && (
            <tr>
              <td className="ed-key">Evidence</td>
              <td className="ed-val ed-evidence">"{edge.evidence}"</td>
            </tr>
          )}
        </tbody>
      </table>

      <div className="ed-hint">Click background to close</div>
    </div>
  );
}
