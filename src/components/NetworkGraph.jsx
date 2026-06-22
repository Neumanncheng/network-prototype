import React, { useEffect, useRef } from 'react';
import cytoscape from 'cytoscape';
import { EDGE_STYLES, riskTier, RISK_COLORS } from '../data/sampleGraph.js';
import './NetworkGraph.css';

export default function NetworkGraph({ graph, onSelectNode, onSelectEdge, hiddenEdgeTypes = [], hiddenNodeTypes = [], hiddenRiskTiers = [] }) {
  const containerRef = useRef(null);
  const cyRef = useRef(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const nodeTypes = ['customer', 'account', 'external', 'ip', 'device'];
    const nodeShape = { customer: 'ellipse', account: 'round-rectangle', external: 'diamond', ip: 'triangle', device: 'hexagon' };
    const nodeSize = { customer: 60, account: 44, external: 52, ip: 36, device: 36 };

    const styles = [];

    styles.push({
      selector: 'node',
      style: {
        'background-color': '#334155',
        label: 'data(label)',
        'font-size': 10,
        'text-valign': 'bottom',
        'text-halign': 'center',
        'text-margin-y': 4,
        color: '#cbd5e1',
        'border-width': 2,
        'border-color': '#475569',
        'min-zoomed-font-size': 6,
      },
    });

    for (const t of nodeTypes) {
      styles.push({
        selector: `node[type = "${t}"]`,
        style: { width: nodeSize[t], height: nodeSize[t], shape: nodeShape[t], 'background-color': '#1e293b', 'border-width': 2, 'border-color': '#475569' },
      });
    }

    for (const [tier, info] of Object.entries(RISK_COLORS)) {
      styles.push({
        selector: `node[riskTier = "${tier}"]`,
        style: { 'border-color': info.color, 'border-width': 3 },
      });
    }

    styles.push({
      selector: 'node[riskTier = "high"]',
      style: { 'shadow-blur': 12, 'shadow-color': '#ef4444', 'shadow-opacity': 0.5 },
    });

    styles.push({
      selector: 'edge',
      style: {
        width: 1, 'line-color': '#475569', 'target-arrow-color': '#475569',
        'target-arrow-shape': 'triangle', 'arrow-scale': 0.7,
        'curve-style': 'bezier', 'text-rotation': 'autorotate',
      },
    });

    for (const [type, st] of Object.entries(EDGE_STYLES)) {
      const s = {
        selector: `edge[type = "${type}"]`,
        style: { width: st.width, 'line-color': st.color, 'target-arrow-color': st.color },
      };
      if (st.dash) { s.style['line-style'] = 'dashed'; s.style['line-dash-pattern'] = st.dash; }
      s.style.label = st.label;
      s.style['font-size'] = 8;
      s.style.color = st.color;
      s.style['text-background-color'] = '#0f172a';
      s.style['text-background-opacity'] = 0.8;
      s.style['text-background-padding'] = 2;
      s.style['edge-text-rotation'] = 'autorotate';
      styles.push(s);
    }

    const enriched = {
      nodes: graph.nodes.map((n) => ({
        ...n,
        data: {
          ...n.data,
          riskScore: n.data.riskScore ?? n.data.risk_score ?? 0,
          riskTier: riskTier(n.data.riskScore ?? n.data.risk_score),
          labelZh: n.data.labelZh ?? n.data.label_zh ?? '',
        },
      })),
      edges: graph.edges,
    };

    let cy;
    try {
      cy = cytoscape({
        container: containerRef.current,
        elements: enriched,
        style: styles,
        layout: {
          name: 'cose',
          idealEdgeLength: 250,
          nodeOverlap: 80,
          refresh: 20,
          fit: true,
          padding: 60,
          randomize: true,
          componentSpacing: 200,
          nodeRepulsion: () => 20000,
          edgeElasticity: () => 60,
          nestingFactor: 15,
          gravity: 0.4,
          numIter: 2500,
          animate: false,
        },
        minZoom: 0.3, maxZoom: 3, wheelSensitivity: 0.3,
      });
    } catch (e) {
      console.error('Cytoscape init failed:', e);
      return;
    }

    cyRef.current = cy;

    // ── Edge click ──
    cy.on('tap', 'edge', (evt) => {
      const edge = evt.target;
      const data = edge.data();
      cy.elements().removeClass('highlighted dimmed');
      edge.addClass('highlighted');
      edge.source().addClass('highlighted');
      edge.target().addClass('highlighted');
      cy.elements().not(edge).not(edge.source()).not(edge.target()).addClass('dimmed');
      onSelectNode(null);
      onSelectEdge?.({
        id: data.id,
        type: data.type,
        source: data.source,
        target: data.target,
        amount: data.amount,
        currency: data.currency,
        date: data.date,
        percentage: data.percentage,
        evidence: data.evidence,
        confidence: data.confidence,
        ip: data.ip,
        sourceLabel: edge.source().data('label') || data.source,
        targetLabel: edge.target().data('label') || data.target,
        sourceType: edge.source().data('type'),
        targetType: edge.target().data('type'),
      });
    });

    // ── Node click ──
    cy.on('tap', 'node', (evt) => {
      const node = evt.target;
      const data = node.data();
      cy.elements().removeClass('highlighted dimmed');
      node.addClass('highlighted');
      node.neighborhood().addClass('highlighted');
      cy.elements().not(node).not(node.neighborhood()).addClass('dimmed');
      onSelectEdge?.(null);
      onSelectNode({
        id: data.id, label: data.label, labelZh: data.labelZh,
        type: data.type, riskScore: data.riskScore, riskTier: data.riskTier,
        country: data.country, bank: data.bank,
        idType: data.idType, idNumber: data.idNumber,
        geo: data.geo, isp: data.isp, os: data.os,
        connections: node.neighborhood().nodes().map((n) => ({
          id: n.data().id, label: n.data().label, type: n.data().type, riskScore: n.data().riskScore,
        })),
        edgeDetails: node.connectedEdges().map((e) => ({
          id: e.data().id, type: e.data().type, source: e.data().source, target: e.data().target,
          amount: e.data().amount, currency: e.data().currency, date: e.data().date,
          percentage: e.data().percentage, evidence: e.data().evidence, confidence: e.data().confidence,
        })),
      });
    });

    // ── Background click ──
    cy.on('tap', (evt) => {
      if (evt.target === cy) {
        cy.elements().removeClass('highlighted dimmed');
        onSelectNode(null);
        onSelectEdge?.(null);
      }
    });

    return () => {
      try { cy.destroy(); } catch (e) { /* ignore */ }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [graph]);

  // ── Apply filters ──
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;
    try {
      cy.nodes().forEach((node) => {
        const type = node.data('type');
        const tier = node.data('riskTier');
        node.style('display', (hiddenNodeTypes.includes(type) || hiddenRiskTiers.includes(tier)) ? 'none' : 'element');
      });
      cy.edges().forEach((edge) => {
        const eType = edge.data('type');
        const srcHidden = edge.source().style('display') === 'none';
        const tgtHidden = edge.target().style('display') === 'none';
        edge.style('display', (hiddenEdgeTypes.includes(eType) || srcHidden || tgtHidden) ? 'none' : 'element');
      });
    } catch (e) { console.error('Filter error:', e); }
  }, [hiddenEdgeTypes, hiddenNodeTypes, hiddenRiskTiers]);

  return (
    <div className="network-graph-wrapper">
      <div ref={containerRef} className="network-graph" />
      <div className="graph-controls">
        <button className="ctrl-btn" onClick={() => { try { cyRef.current?.zoom(cyRef.current.zoom() * 1.3); } catch (e) {} }}>＋</button>
        <button className="ctrl-btn" onClick={() => { try { cyRef.current?.zoom(cyRef.current.zoom() * 0.7); } catch (e) {} }}>−</button>
        <button className="ctrl-btn" onClick={() => { try { cyRef.current?.fit(undefined, 30); } catch (e) {} }}>⊡</button>
        <button className="ctrl-btn" onClick={() => {
          try {
            const cy = cyRef.current;
            if (!cy) return;
            cy.layout({ name: 'cose', idealEdgeLength: 250, nodeOverlap: 80, refresh: 20, fit: true, padding: 60, randomize: true, componentSpacing: 200, nodeRepulsion: () => 20000, edgeElasticity: () => 60, nestingFactor: 15, gravity: 0.4, numIter: 2500, animate: false }).run();
          } catch (e) { console.error('Relayout error:', e); }
        }}>⟳</button>
      </div>
      <div className="graph-watermark">Drag to pan · Scroll to zoom · Click a node</div>
    </div>
  );
}
