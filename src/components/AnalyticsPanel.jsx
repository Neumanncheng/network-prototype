import React, { useState, useEffect } from 'react';
import { api } from '../api.js';
import PatternPanel from './PatternPanel.jsx';
import './AnalyticsPanel.css';

export default function AnalyticsPanel() {
  const [tab, setTab] = useState('centrality');
  const [centrality, setCentrality] = useState(null);
  const [communities, setCommunities] = useState(null);
  const [temporal, setTemporal] = useState(null);
  const [loading, setLoading] = useState({});
  const [errors, setErrors] = useState({});

  useEffect(() => {
    if (tab === 'centrality' && !centrality && !loading.centrality) {
      setLoading(p => ({...p, centrality: true}));
      api.getTopCentral('pagerank', 8)
        .then(d => setCentrality(d))
        .catch(e => setErrors(p => ({...p, centrality: e.message})))
        .finally(() => setLoading(p => ({...p, centrality: false})));
    }
    if (tab === 'communities' && !communities && !loading.communities) {
      setLoading(p => ({...p, communities: true}));
      api.getCommunities()
        .then(d => setCommunities(d))
        .catch(e => setErrors(p => ({...p, communities: e.message})))
        .finally(() => setLoading(p => ({...p, communities: false})));
    }
    if (tab === 'temporal' && !temporal && !loading.temporal) {
      setLoading(p => ({...p, temporal: true}));
      api.getTemporal()
        .then(d => setTemporal(d))
        .catch(e => setErrors(p => ({...p, temporal: e.message})))
        .finally(() => setLoading(p => ({...p, temporal: false})));
    }
  }, [tab, centrality, communities, temporal, loading]);

  return (
    <div className="analytics-panel">
      {/* Sub-tabs */}
      <div className="an-tabs">
        {['centrality', 'communities', 'patterns', 'temporal'].map(t => (
          <button
            key={t}
            className={`an-tab ${tab === t ? 'active' : ''}`}
            onClick={() => setTab(t)}
          >
            {t === 'centrality' && '📐'} {t === 'communities' && '👥'} {t === 'patterns' && '🔍'} {t === 'temporal' && '⏱'}
            {' '}{t.charAt(0).toUpperCase() + t.slice(1)}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {tab === 'centrality' && (
        <div className="an-content">
          <h3>📐 Top Central Nodes (PageRank)</h3>
          {loading.centrality && <div className="an-loading">Loading...</div>}
          {errors.centrality && <div className="an-error">⚠️ {errors.centrality}</div>}
          {centrality && (
            <div className="an-list">
              {centrality.map((node, i) => (
                <div key={node.id} className="an-rank-row">
                  <span className="an-rank">#{i + 1}</span>
                  <div className="an-rank-info">
                    <span className="an-rank-label">{node.label}</span>
                    <span className="an-rank-type">{node.type}</span>
                  </div>
                  <div className="an-rank-bar-wrap">
                    <div
                      className="an-rank-bar"
                      style={{ width: `${Math.min(node.score, 100)}%`, background: i < 3 ? '#ef4444' : i < 5 ? '#f59e0b' : '#3b82f6' }}
                    />
                  </div>
                  <span className="an-rank-score">{node.score.toFixed(1)}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {tab === 'communities' && (
        <div className="an-content">
          <h3>👥 Detected Communities</h3>
          {loading.communities && <div className="an-loading">Loading...</div>}
          {errors.communities && <div className="an-error">⚠️ {errors.communities}</div>}
          {communities && (
            <div className="an-communities">
              {communities.communities.map((c) => (
                <div key={c.community_id} className="an-comm-card">
                  <div className="an-comm-header">
                    <span>Community #{c.community_id}</span>
                    <span className="an-comm-size">{c.size} members</span>
                    <span className="an-comm-risk" style={{
                      color: c.avg_risk_score >= 70 ? '#ef4444' : c.avg_risk_score >= 30 ? '#f59e0b' : '#22c55e'
                    }}>
                      Risk: {c.avg_risk_score}
                    </span>
                  </div>
                  <div className="an-comm-members">
                    {c.members.map(m => (
                      <span key={m.id} className="an-comm-member">
                        {m.label}
                        <small style={{color: '#64748b', marginLeft: 4}}>({m.type})</small>
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {tab === 'patterns' && <PatternPanel />}

      {tab === 'temporal' && (
        <div className="an-content">
          <h3>⏱ Temporal Anomalies</h3>
          {loading.temporal && <div className="an-loading">Loading...</div>}
          {errors.temporal && <div className="an-error">⚠️ {errors.temporal}</div>}
          {temporal && (
            <>
              {/* Monthly summary */}
              {temporal.monthly_summary && (
                <div className="an-temporal-bars">
                  <div className="an-subtitle">Monthly Transactions</div>
                  <div className="an-bar-chart">
                    {temporal.monthly_summary.map(m => {
                      const maxCount = Math.max(...temporal.monthly_summary.map(x => x.count), 1);
                      return (
                        <div key={m.month} className="an-bar-col">
                          <div className="an-col-label">{m.month.slice(5)}</div>
                          <div className="an-col-track">
                            <div
                              className="an-col-fill"
                              style={{ height: `${(m.count / maxCount) * 100}%` }}
                            />
                          </div>
                          <div className="an-col-count">{m.count}</div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Anomalies */}
              {temporal.anomalies && temporal.anomalies.length > 0 ? (
                <div className="an-temporal-anomalies">
                  <div className="an-subtitle">⚠️ Detected Anomalies</div>
                  {temporal.anomalies.map((a, i) => (
                    <div key={i} className="an-anomaly-item">
                      <span className="an-anomaly-reason">{a.reason}</span>
                      {a.month && <span className="an-anomaly-meta">{a.month}</span>}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="an-loading" style={{padding: 12}}>No temporal anomalies detected.</div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}
