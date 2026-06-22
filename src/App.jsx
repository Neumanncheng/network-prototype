import React, { useState, useEffect, useCallback } from 'react';
import { api } from './api.js';
import NetworkGraph from './components/NetworkGraph.jsx';
import NodeDetail from './components/NodeDetail.jsx';
import EdgeDetail from './components/EdgeDetail.jsx';
import RiskScorePanel from './components/RiskScorePanel.jsx';
import LegendPanel from './components/LegendPanel.jsx';
import AnalyticsPanel from './components/AnalyticsPanel.jsx';
import LoginPage from './components/LoginPage.jsx';
import './App.css';

export default function App() {
  // Check if redirected to login due to expired token
  const [authenticated, setAuthenticated] = useState(
    window.location.hash !== '#login' && api.isAuthenticated()
  );
  const [graph, setGraph] = useState(null);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [selectedNode, setSelectedNode] = useState(null);
  const [sidebarTab, setSidebarTab] = useState('node');
  const [hiddenEdgeTypes, setHiddenEdgeTypes] = useState([]);
  const [hiddenNodeTypes, setHiddenNodeTypes] = useState([]);
  const [hiddenRiskTiers, setHiddenRiskTiers] = useState([]);
  const [riskListView, setRiskListView] = useState(null);
  const [selectedEdge, setSelectedEdge] = useState(null);

  const toggleFilter = (setter) => (value) => {
    setter((prev) =>
      prev.includes(value) ? prev.filter((t) => t !== value) : [...prev, value]
    );
  };

  const toggleEdgeType = toggleFilter(setHiddenEdgeTypes);
  const toggleNodeType = toggleFilter(setHiddenNodeTypes);
  const toggleRiskTier = toggleFilter(setHiddenRiskTiers);

  // ── Get customer nodes by risk tier ────────────────────
  const nodeListByRisk = useCallback((tier) => {
    if (!graph) return [];
    return graph.nodes
      .filter((n) => n.data.type === 'customer')
      .filter((n) => {
        const score = n.data.riskScore ?? n.data.risk_score ?? 0;
        if (tier === 'high') return score >= 70;
        if (tier === 'medium') return score >= 30 && score < 70;
        return score < 30;
      })
      .map((n) => ({
        id: n.data.id,
        label: n.data.label,
        labelZh: n.data.labelZh ?? n.data.label_zh ?? '',
        riskScore: n.data.riskScore ?? n.data.risk_score ?? 0,
        riskTier: tier,
        country: n.data.country ?? '',
        idType: n.data.idType ?? n.data.id_type ?? '',
        idNumber: n.data.idNumber ?? n.data.id_number ?? '',
      }))
      .sort((a, b) => b.riskScore - a.riskScore);
  }, [graph]);

  const handleSelectNode = useCallback((node) => {
    setSelectedNode(node);
    if (node) setSelectedEdge(null);
  }, []);

  const handleSelectEdge = useCallback((edge) => {
    setSelectedEdge(edge);
    if (edge) setSelectedNode(null);
  }, []);

  const handleLogin = useCallback((token) => {
    setAuthenticated(true);
  }, []);

  const handleLogout = useCallback(() => {
    api.logout();
    setAuthenticated(false);
    setGraph(null);
    setStats(null);
    setError(null);
    setSelectedNode(null);
    setSelectedEdge(null);
    setRiskListView(null);
  }, []);

  const handleCloseAll = useCallback(() => {
    setSelectedNode(null);
    setSelectedEdge(null);
  }, []);

  const handleRiskClick = (tier) => {
    setRiskListView(riskListView === tier ? null : tier);
  };

  const riskList = riskListView ? nodeListByRisk(riskListView) : [];

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [g, s] = await Promise.all([api.getGraph(), api.getStats()]);
      setGraph(g);
      setStats(s);
    } catch (err) {
      // If token expired, redirect to login
      if (err.message === '401' || (err.message && err.message.includes('401'))) {
        api.logout();
        setAuthenticated(false);
        setGraph(null);
        setStats(null);
        return;
      }
      setError(err.message || 'Failed to connect to backend');
    } finally {
      setLoading(false);
    }
  }, []);

  // Load data when authenticated for the first time (graph is null)
  useEffect(() => {
    if (authenticated && !graph) {
      loadData();
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [authenticated]);

  if (!authenticated) return <LoginPage onLogin={handleLogin} />;

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-left">
          <h1 className="app-title">🔗 Network Analytics Engine</h1>
          <span className="app-subtitle">Relationship Graph · Risk Propagation · AML Screening</span>
        </div>
        {stats && (
          <div className="header-right">
            <span className="badge badge-nodes">{stats.totalNodes} nodes</span>
            <span className="badge badge-edges">{stats.totalEdges} edges</span>
            <span className="badge badge-customers">{stats.customers} customers</span>
            {stats.communities > 0 && (
              <span className="badge badge-communities">{stats.communities} communities</span>
            )}
          </div>
        )}
        <button
          onClick={handleLogout}
          style={{
            marginLeft: 12, padding: '4px 10px', border: '1px solid #334155',
            borderRadius: 6, background: 'transparent', color: '#64748b',
            fontSize: 11, cursor: 'pointer', flexShrink: 0,
          }}
          title="Sign out"
        >🚪</button>
      </header>

      <div className="app-body">
        <div className="graph-area">
          {loading && (
            <div className="graph-overlay">
              <div className="spinner" />
              <p>Loading network graph...</p>
            </div>
          )}
          {error && (
            <div className="graph-overlay error-overlay">
              <p>⚠️ {error}</p>
              <button className="retry-btn" onClick={loadData}>Retry</button>
            </div>
          )}
          {graph && (
            <NetworkGraph
              graph={graph}
              onSelectNode={handleSelectNode}
              onSelectEdge={handleSelectEdge}
              hiddenEdgeTypes={hiddenEdgeTypes}
              hiddenNodeTypes={hiddenNodeTypes}
              hiddenRiskTiers={hiddenRiskTiers}
            />
          )}
        </div>

        <aside className="sidebar">
          <div className="sidebar-tabs">
            <button
              className={`sidebar-tab ${sidebarTab === 'node' ? 'active' : ''}`}
              onClick={() => setSidebarTab('node')}
            >📋 Node</button>
            <button
              className={`sidebar-tab ${sidebarTab === 'analytics' ? 'active' : ''}`}
              onClick={() => setSidebarTab('analytics')}
            >📊 Analytics</button>
          </div>

          {sidebarTab === 'node' ? (
            <>
              {selectedEdge ? (
                <EdgeDetail edge={selectedEdge} onClose={() => setSelectedEdge(null)} />
              ) : selectedNode ? (
                <>
                  <NodeDetail node={selectedNode} onClose={() => setSelectedNode(null)} />
                  <RiskScorePanel nodeId={selectedNode.id} />
                </>
              ) : (
                <>
                  {stats && (
                    <div className="sidebar-section">
                      <h3>📊 Overview</h3>
                      <div className="overview-grid">
                        <div
                          className={`overview-item overview-clickable ${riskListView === 'high' ? 'overview-active' : ''}`}
                          onClick={() => handleRiskClick('high')}
                        >
                          <span className="overview-value">{stats.highRisk}</span>
                          <span className="overview-label">High Risk</span>
                        </div>
                        <div
                          className={`overview-item overview-clickable ${riskListView === 'medium' ? 'overview-active' : ''}`}
                          onClick={() => handleRiskClick('medium')}
                        >
                          <span className="overview-value">{stats.medRisk}</span>
                          <span className="overview-label">Medium Risk</span>
                        </div>
                        <div
                          className={`overview-item overview-clickable ${riskListView === 'low' ? 'overview-active' : ''}`}
                          onClick={() => handleRiskClick('low')}
                        >
                          <span className="overview-value">{stats.lowRisk}</span>
                          <span className="overview-label">Low Risk</span>
                        </div>
                        <div className="overview-item">
                          <span className="overview-value">{stats.suspiciousPatterns}</span>
                          <span className="overview-label">⚠ Patterns</span>
                        </div>
                      </div>

                      {/* Risk node list */}
                      {riskListView && (
                        <div className="risk-node-list">
                          <div className="risk-node-list-header">
                            {riskListView === 'high' ? '🔴' : riskListView === 'medium' ? '🟡' : '🟢'}
                            {' '}
                            {riskListView === 'high' ? 'High' : riskListView === 'medium' ? 'Medium' : 'Low'} Risk Customers
                            <span className="risk-node-count">{riskList.length}</span>
                          </div>
                          {riskList.length === 0 ? (
                            <div className="risk-node-empty">No {riskListView} risk customers found</div>
                          ) : (
                            <div className="risk-node-items">
                              {riskList.map((node) => (
                                <div
                                  key={node.id}
                                  className="risk-node-item"
                                  onClick={() => setSelectedNode(node)}
                                >
                                  <div className="risk-node-left">
                                    <span className="risk-node-label">{node.label}</span>
                                    {node.labelZh && <span className="risk-node-zh">{node.labelZh}</span>}
                                  </div>
                                  <div className="risk-node-right">
                                    <span
                                      className="risk-node-score"
                                      style={{ color: riskListView === 'high' ? '#ef4444' : riskListView === 'medium' ? '#f59e0b' : '#22c55e' }}
                                    >
                                      {node.riskScore}
                                    </span>
                                    {node.country && <span className="risk-node-country">{node.country}</span>}
                                  </div>
                                </div>
                              ))}
                            </div>
                          )}
                          <div className="risk-node-hint">Click a customer to inspect details</div>
                        </div>
                      )}
                    </div>
                  )}
                  <LegendPanel
                    hiddenEdgeTypes={hiddenEdgeTypes}
                    onToggleEdgeType={toggleEdgeType}
                    hiddenNodeTypes={hiddenNodeTypes}
                    onToggleNodeType={toggleNodeType}
                    hiddenRiskTiers={hiddenRiskTiers}
                    onToggleRiskTier={toggleRiskTier}
                  />
                  <div className="sidebar-hint">
                    <p>💡 Click any node to inspect details, risk scores, and connection paths.</p>
                    <p>📊 Switch to <strong>Analytics</strong> tab for centrality, communities & patterns.</p>
                  </div>
                </>
              )}
            </>
          ) : (
            <AnalyticsPanel />
          )}
        </aside>
      </div>
    </div>
  );
}
