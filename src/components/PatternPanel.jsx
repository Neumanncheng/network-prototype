import React, { useState, useEffect } from 'react';
import { api } from '../api.js';
import './PatternPanel.css';

const PATTERN_ICONS = { fan_out: '📤', fan_in: '📥', cycles: '🔄' };

export default function PatternPanel() {
  const [patterns, setPatterns] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    api.getPatterns()
      .then(d => { if (!cancelled) setPatterns(d); })
      .catch(e => { if (!cancelled) setError(e.message); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, []);

  if (loading) return <div className="an-content"><div className="an-loading">Loading patterns...</div></div>;
  if (error) return <div className="an-content"><div className="an-error">⚠️ {error}</div></div>;
  if (!patterns) return <div className="an-content"><div className="an-loading">No pattern data.</div></div>;

  const totalPatterns = (patterns.fan_out?.length || 0) + (patterns.fan_in?.length || 0) + (patterns.cycles?.length || 0);

  return (
    <div className="an-content">
      <h3>🔍 Detected Patterns</h3>
      <div className="pt-summary">{totalPatterns} pattern{totalPatterns !== 1 ? 's' : ''} found</div>

      {/* Fan-out */}
      {patterns.fan_out?.length > 0 && (
        <div className="pt-group">
          <div className="pt-group-title">📤 Fan-out Patterns ({patterns.fan_out.length})</div>
          {patterns.fan_out.map((fo, i) => (
            <div key={i} className="pt-card pt-fanout">
              <div className="pt-card-header">
                <span className="pt-node-label">{fo.label}</span>
                <span className="pt-badge">{fo.out_degree} outgoing</span>
              </div>
              <div className="pt-targets">
                {fo.targets.map(t => (
                  <span key={t.id} className="pt-target">{t.label}</span>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Fan-in */}
      {patterns.fan_in?.length > 0 && (
        <div className="pt-group">
          <div className="pt-group-title">📥 Fan-in Patterns ({patterns.fan_in.length})</div>
          {patterns.fan_in.map((fi, i) => (
            <div key={i} className="pt-card pt-fanin">
              <div className="pt-card-header">
                <span className="pt-node-label">{fi.label}</span>
                <span className="pt-badge">{fi.in_degree} incoming</span>
              </div>
              <div className="pt-targets">
                {fi.sources.map(s => (
                  <span key={s.id} className="pt-target">{s.label}</span>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Cycles */}
      {patterns.cycles?.length > 0 && (
        <div className="pt-group">
          <div className="pt-group-title">🔄 Cyclic Patterns ({patterns.cycles.length})</div>
          {patterns.cycles.map((cycle, i) => (
            <div key={i} className="pt-card pt-cycle">
              <div className="pt-card-header">
                <span className="pt-badge">{cycle.length}-node cycle</span>
              </div>
              <div className="pt-cycle-nodes">
                {cycle.nodes.map((n, j) => (
                  <span key={n.id} className="pt-cycle-step">
                    {n.label}{j < cycle.nodes.length - 1 ? ' → ' : ''}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {totalPatterns === 0 && (
        <div className="pt-empty">No suspicious patterns detected in the current graph.</div>
      )}
    </div>
  );
}
