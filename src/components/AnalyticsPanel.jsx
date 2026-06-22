import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../api.js';
import PatternPanel from './PatternPanel.jsx';
import './AnalyticsPanel.css';

const TABS = [
  { key: 'centrality', icon: '📐', label: 'Centrality' },
  { key: 'communities', icon: '👥', label: 'Communities' },
  { key: 'components', icon: '🔗', label: 'Clusters' },
  { key: 'bfs', icon: '🌊', label: 'Expand' },
  { key: 'dijkstra', icon: '🛤️', label: 'Risk Path' },
  { key: 'patterns', icon: '🔍', label: 'Patterns' },
  { key: 'temporal', icon: '⏱', label: 'Temporal' },
];

function useData(key, fetcher) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    fetcher()
      .then(setData)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, [fetcher]);

  return { data, loading, error, load };
}

export default function AnalyticsPanel() {
  const [tab, setTab] = useState('centrality');

  // Individual lazy-loading states
  const [centrality, setCentrality] = useState(null);
  const [communities, setCommunities] = useState(null);
  const [components, setComponents] = useState(null);
  const [bfsData, setBfsData] = useState(null);
  const [dijkstra, setDijkstra] = useState(null);
  const [temporal, setTemporal] = useState(null);
  const [loading, setLoading] = useState({});
  const [errors, setErrors] = useState({});

  // BFS + Dijkstra input states
  const [bfsSeed, setBfsSeed] = useState('');
  const [bfsDepth, setBfsDepth] = useState(3);
  const [djSource, setDjSource] = useState('');
  const [djTarget, setDjTarget] = useState('');

  useEffect(() => {
    const loaders = {
      centrality: () => {
        if (!centrality && !loading.centrality) {
          setLoading(p => ({...p, centrality: true}));
          api.getTopCentral('pagerank', 8)
            .then(d => setCentrality(d))
            .catch(e => setErrors(p => ({...p, centrality: e.message})))
            .finally(() => setLoading(p => ({...p, centrality: false})));
        }
      },
      communities: () => {
        if (!communities && !loading.communities) {
          setLoading(p => ({...p, communities: true}));
          api.getCommunities()
            .then(d => setCommunities(d))
            .catch(e => setErrors(p => ({...p, communities: e.message})))
            .finally(() => setLoading(p => ({...p, communities: false})));
        }
      },
      components: () => {
        if (!components && !loading.components) {
          setLoading(p => ({...p, components: true}));
          api.getSharedComponents()
            .then(d => setComponents(d))
            .catch(e => setErrors(p => ({...p, components: e.message})))
            .finally(() => setLoading(p => ({...p, components: false})));
        }
      },
      temporal: () => {
        if (!temporal && !loading.temporal) {
          setLoading(p => ({...p, temporal: true}));
          api.getTemporal()
            .then(d => setTemporal(d))
            .catch(e => setErrors(p => ({...p, temporal: e.message})))
            .finally(() => setLoading(p => ({...p, temporal: false})));
        }
      },
    };
    loaders[tab]?.();
  }, [tab, centrality, communities, components, temporal, loading]);

  const runBfs = async () => {
    if (!bfsSeed.trim()) return;
    setLoading(p => ({...p, bfs: true}));
    setErrors(p => ({...p, bfs: null}));
    try {
      const data = await api.bfsExpand(bfsSeed.trim(), bfsDepth);
      setBfsData(data);
    } catch (e) {
      setErrors(p => ({...p, bfs: e.message}));
    } finally {
      setLoading(p => ({...p, bfs: false}));
    }
  };

  const runDijkstra = async () => {
    if (!djSource.trim() || !djTarget.trim()) return;
    setLoading(p => ({...p, dijkstra: true}));
    setErrors(p => ({...p, dijkstra: null}));
    try {
      const data = await api.dijkstraPath(djSource.trim(), djTarget.trim());
      setDijkstra(data);
    } catch (e) {
      setErrors(p => ({...p, dijkstra: e.message}));
    } finally {
      setLoading(p => ({...p, dijkstra: false}));
    }
  };

  return (
    <div className="analytics-panel">
      <div className="an-tabs">
        {TABS.map(t => (
          <button
            key={t.key}
            className={`an-tab ${tab === t.key ? 'active' : ''}`}
            onClick={() => setTab(t.key)}
          >
            {t.icon} {t.label}
          </button>
        ))}
      </div>

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
                    <div className="an-rank-bar" style={{ width: `${Math.min(node.score, 100)}%`, background: i < 3 ? '#ef4444' : i < 5 ? '#f59e0b' : '#3b82f6' }} />
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
              {communities.communities.filter(c => c.size > 1).map(c => (
                <div key={c.community_id} className="an-comm-card">
                  <div className="an-comm-header">
                    <span>Community #{c.community_id}</span>
                    <span className="an-comm-size">{c.size} members</span>
                    <span className="an-comm-risk" style={{ color: c.avg_risk_score >= 70 ? '#ef4444' : c.avg_risk_score >= 30 ? '#f59e0b' : '#22c55e' }}>
                      Risk: {c.avg_risk_score}
                    </span>
                  </div>
                  <div className="an-comm-members">
                    {c.members.map(m => (
                      <span key={m.id} className="an-comm-member">
                        {m.label}
                        <small style={{ color: '#64748b', marginLeft: 4 }}>({m.type})</small>
                      </span>
                    ))}
                  </div>
                </div>
              ))}
              <div className="an-loading" style={{ padding: 8, fontSize: 11 }}>
                {communities.communities.filter(c => c.size === 1).length} singleton communities (IPs, devices) not shown
              </div>
            </div>
          )}
        </div>
      )}

      {tab === 'components' && (
        <div className="an-content">
          <h3>🔗 Shared-Identifier Clusters</h3>
          <p className="an-desc">Groups of nodes connected by shared IPs, phones, emails, addresses, or devices</p>
          {loading.components && <div className="an-loading">Loading...</div>}
          {errors.components && <div className="an-error">⚠️ {errors.components}</div>}
          {components && (
            <div className="an-communities">
              {components.components.filter(c => c.size > 1).map(c => (
                <div key={c.component_id} className="an-comm-card">
                  <div className="an-comm-header">
                    <span>Cluster #{c.component_id}</span>
                    <span className="an-comm-size">{c.size} nodes</span>
                    <span className="an-comm-risk" style={{ color: c.avg_risk_score >= 70 ? '#ef4444' : c.avg_risk_score >= 30 ? '#f59e0b' : '#22c55e' }}>
                      Risk: {c.avg_risk_score}
                    </span>
                  </div>
                  <div className="an-card-stats" style={{ display: 'flex', gap: 6, marginBottom: 6 }}>
                    <span className="an-comm-member" style={{ fontSize: 9 }}>👤 {c.composition.customers} customers</span>
                    <span className="an-comm-member" style={{ fontSize: 9 }}>🏦 {c.composition.accounts} accounts</span>
                    <span className="an-comm-member" style={{ fontSize: 9 }}>🏢 {c.composition.external_entities} entities</span>
                    <span className="an-comm-member" style={{ fontSize: 9 }}>🌐 {c.composition.ip_addresses} IPs</span>
                  </div>
                  <div className="an-comm-members">
                    {c.members.map(m => (
                      <span key={m.id} className="an-comm-member">
                        {m.label}
                        <small style={{ color: '#64748b', marginLeft: 4 }}>({m.type})</small>
                      </span>
                    ))}
                  </div>
                </div>
              ))}
              {components.components.filter(c => c.size === 1).length > 0 && (
                <div className="an-loading" style={{ padding: 8, fontSize: 11 }}>
                  +{components.components.filter(c => c.size === 1).length} isolated nodes (no shared identifiers)
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {tab === 'bfs' && (
        <div className="an-content">
          <h3>🌊 Network Expansion (BFS)</h3>
          <p className="an-desc">Expand outward from a seed node to see all connections within N hops</p>
          <div className="an-input-row">
            <input
              className="an-input"
              placeholder="Seed node ID (e.g. n-1)"
              value={bfsSeed}
              onChange={e => setBfsSeed(e.target.value)}
            />
            <input
              className="an-input an-input-sm"
              type="number"
              min={1}
              max={6}
              value={bfsDepth}
              onChange={e => setBfsDepth(parseInt(e.target.value) || 3)}
              title="Max depth"
            />
            <button className="an-input-btn" onClick={runBfs} disabled={loading.bfs || !bfsSeed.trim()}>
              {loading.bfs ? '⟳' : '▶'} Expand
            </button>
          </div>
          {errors.bfs && <div className="an-error">⚠️ {errors.bfs}</div>}

          {bfsData && !bfsData.error && (
            <div className="an-bfs-result">
              <div className="an-subtitle" style={{ marginTop: 8 }}>
                From <strong>{bfsData.seed_label}</strong> ({bfsData.seed_type})
                — reached {bfsData.total_reached} nodes across {bfsData.expansion.length} level(s)
              </div>
              {bfsData.expansion.map(level => (
                <div key={level.depth} className="an-bfs-level">
                  <div className="an-bfs-level-title">
                    Depth {level.depth}
                    <span className="an-badge an-badge-depth">{level.node_count} nodes</span>
                  </div>
                  <div className="an-rank-items">
                    {level.nodes.map(n => (
                      <div key={n.id} className="an-rank-row" style={{ padding: '4px 6px' }}>
                        <span className="an-rank-label" style={{ flex: 1 }}>{n.label}</span>
                        <span className="an-rank-type">{n.type}</span>
                        {n.risk_score > 0 && (
                          <span className="an-rank-score" style={{ width: 'auto', marginLeft: 6, color: n.risk_score >= 70 ? '#ef4444' : '#f59e0b' }}>
                            {n.risk_score}
                          </span>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
          {bfsData?.error && <div className="an-error">⚠️ {bfsData.error}</div>}
        </div>
      )}

      {tab === 'dijkstra' && (
        <div className="an-content">
          <h3>🛤️ Lowest-Risk Path</h3>
          <p className="an-desc">Find the lowest-risk connection path between two nodes. Weights: transaction amount, shared IDs, LLM confidence.</p>
          <div className="an-input-row">
            <input
              className="an-input"
              placeholder="Source node ID (e.g. n-1)"
              value={djSource}
              onChange={e => setDjSource(e.target.value)}
            />
            <input
              className="an-input"
              placeholder="Target node ID (e.g. n-14)"
              value={djTarget}
              onChange={e => setDjTarget(e.target.value)}
            />
            <button className="an-input-btn" onClick={runDijkstra} disabled={loading.dijkstra || !djSource.trim() || !djTarget.trim()}>
              {loading.dijkstra ? '⟳' : '▶'} Find
            </button>
          </div>
          {errors.dijkstra && <div className="an-error">⚠️ {errors.dijkstra}</div>}

          {dijkstra && !dijkstra.error && (
            <div className="an-dj-result">
              <div className="an-subtitle" style={{ marginTop: 8 }}>
                Path: <strong>{dijkstra.nodes[0]?.label}</strong> → <strong>{dijkstra.nodes[dijkstra.nodes.length - 1]?.label}</strong>
                <span className="an-badge an-badge-depth" style={{ marginLeft: 8 }}>
                  {dijkstra.length} hop{dijkstra.length > 1 ? 's' : ''}
                </span>
                <span className="an-badge" style={{ marginLeft: 4, background: '#3b1e5f', color: '#c4b5fd' }}>
                  Risk: {dijkstra.total_risk_weight}
                </span>
              </div>

              <div className="an-dj-steps">
                {dijkstra.edges.map((e, i) => {
                  const fromNode = dijkstra.nodes.find(n => n.id === e.source);
                  const toNode = dijkstra.nodes.find(n => n.id === e.target);
                  return (
                    <div key={i} className="an-dj-step">
                      <div className="an-dj-step-nodes">
                        <span className="an-dj-node">{fromNode?.label || e.source}</span>
                        <span className="an-dj-arrow">→</span>
                        <span className="an-dj-node">{toNode?.label || e.target}</span>
                      </div>
                      <div className="an-dj-step-meta">
                        <span className="edge-type-tag" style={{ fontSize: 9, padding: '1px 5px' }}>
                          {e.type?.replace('_', ' ') || 'connected'}
                        </span>
                        {e.amount && <span className="edge-meta" style={{ fontSize: 10 }}>{e.currency || ''} ${Number(e.amount).toLocaleString()}</span>}
                        <span className="edge-meta" style={{ fontSize: 10, fontWeight: 600 }}>weight: {e.weight}</span>
                      </div>
                    </div>
                  );
                })}
              </div>

              <div className="an-loading" style={{ padding: 6, fontSize: 10 }}>
                Lower weight = lower risk path. Shared IDs, high transaction amounts, and low-confidence LLM edges increase weight.
              </div>
            </div>
          )}
          {dijkstra?.error && <div className="an-error">⚠️ {dijkstra.error}</div>}
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
                            <div className="an-col-fill" style={{ height: `${(m.count / maxCount) * 100}%` }} />
                          </div>
                          <div className="an-col-count">{m.count}</div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

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
                <div className="an-loading" style={{ padding: 12 }}>No temporal anomalies detected.</div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}
