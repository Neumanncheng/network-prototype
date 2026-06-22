import React from 'react';
import { EDGE_STYLES, RISK_COLORS } from '../data/sampleGraph.js';
import './LegendPanel.css';

const NODE_TYPE_LABELS = { customer: 'Customer', account: 'Account', external: 'External Entity', ip: 'IP Address', device: 'Device' };

export default function LegendPanel({
  hiddenEdgeTypes = [], onToggleEdgeType,
  hiddenNodeTypes = [], onToggleNodeType,
  hiddenRiskTiers = [], onToggleRiskTier,
}) {
  const totalHidden = hiddenEdgeTypes.length + hiddenNodeTypes.length + hiddenRiskTiers.length;

  return (
    <div className="sidebar-section legend-panel">
      <h3>📖 Legend <span className="legend-hint">(click to hide/show)</span></h3>

      {/* Risk levels — clickable */}
      <div className="legend-group">
        <div className="legend-group-title">Node Risk</div>
        <div className="legend-items">
          {Object.entries(RISK_COLORS).map(([tier, info]) => {
            const isHidden = hiddenRiskTiers.includes(tier);
            return (
              <div
                key={tier}
                className={`legend-row legend-clickable ${isHidden ? 'legend-hidden' : ''}`}
                onClick={() => onToggleRiskTier?.(tier)}
              >
                <span className="legend-swatch legend-border" style={{ borderColor: isHidden ? '#334155' : info.color }} />
                <span className="legend-label">{info.label}</span>
                <span className={`legend-toggle ${isHidden ? '' : 'legend-toggle-on'}`}>
                  {isHidden ? '○' : '●'}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Node types — clickable */}
      <div className="legend-group">
        <div className="legend-group-title">Node Types</div>
        <div className="legend-items legend-shapes">
          {Object.entries(NODE_TYPE_LABELS).map(([type, label]) => {
            const isHidden = hiddenNodeTypes.includes(type);
            return (
              <div
                key={type}
                className={`legend-row legend-clickable ${isHidden ? 'legend-hidden' : ''}`}
                onClick={() => onToggleNodeType?.(type)}
              >
                <span className={`legend-shape shape-${type}`} style={isHidden ? { borderColor: '#334155', background: '#334155' } : {}} />
                <span className="legend-label">{label}</span>
                <span className={`legend-toggle ${isHidden ? '' : 'legend-toggle-on'}`}>
                  {isHidden ? '○' : '●'}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Edge types — clickable */}
      <div className="legend-group">
        <div className="legend-group-title">Edge Types</div>
        <div className="legend-items">
          {Object.entries(EDGE_STYLES).map(([type, st]) => {
            const isHidden = hiddenEdgeTypes.includes(type);
            return (
              <div
                key={type}
                className={`legend-row legend-clickable ${isHidden ? 'legend-hidden' : ''}`}
                onClick={() => onToggleEdgeType?.(type)}
              >
                <span className="legend-line" style={{
                  borderTop: `${st.width}px ${st.dash ? 'dashed' : 'solid'} ${isHidden ? '#334155' : st.color}`,
                }} />
                <span className="legend-label">{st.label}</span>
                <span className={`legend-toggle ${isHidden ? '' : 'legend-toggle-on'}`}>
                  {isHidden ? '○' : '●'}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {totalHidden > 0 && (
        <div className="legend-status">
          {totalHidden} item{totalHidden > 1 ? 's' : ''} hidden — click to show
        </div>
      )}
    </div>
  );
}
