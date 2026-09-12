import React from 'react';
import { useSelector } from 'react-redux';
import { Target, ShieldCheck, FileCheck, Brain } from 'lucide-react';

export const AnalysisResultsPanel = () => {
  const { analysis } = useSelector((state) => state.complaintForm);
  const rootCauses = analysis?.root_cause_recommendations || [];
  const capas = analysis?.capa_recommendations || [];
  const summary = analysis?.executive_summary || '';

  if (!summary && rootCauses.length === 0 && capas.length === 0) {
    return null;
  }

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '20px', marginBottom: '24px' }}>
      
      {/* Executive Summary Card */}
      {summary && (
        <div className="glass-panel" style={{ padding: '20px', gridColumn: '1 / -1' }}>
          <h4 style={{ fontSize: '0.95rem', display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '10px', color: 'var(--text-highlight)' }}>
            <FileCheck size={18} /> Executive Complaint Summary
          </h4>
          <p style={{ fontSize: '0.88rem', color: 'var(--text-main)', lineHeight: '1.6' }}>
            {summary}
          </p>
        </div>
      )}

      {/* Root Cause Recommendations Card */}
      <div className="glass-panel" style={{ padding: '20px' }}>
        <h4 style={{ fontSize: '0.95rem', display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '14px', color: '#a78bfa' }}>
          <Brain size={18} /> Root Cause Analysis (5-Why / Fishbone)
        </h4>
        <ul style={{ paddingLeft: '18px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
          {rootCauses.map((rc, idx) => (
            <li key={idx} style={{ fontSize: '0.82rem', color: 'var(--text-muted)', lineHeight: '1.5' }}>
              {rc}
            </li>
          ))}
        </ul>
      </div>

      {/* CAPA Recommendations Card */}
      <div className="glass-panel" style={{ padding: '20px' }}>
        <h4 style={{ fontSize: '0.95rem', display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '14px', color: 'var(--severity-low)' }}>
          <ShieldCheck size={18} /> CAPA Recommendations (ISO 13485 / GxP)
        </h4>
        <ul style={{ paddingLeft: '18px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
          {capas.map((capa, idx) => (
            <li key={idx} style={{ fontSize: '0.82rem', color: 'var(--text-muted)', lineHeight: '1.5' }}>
              {capa}
            </li>
          ))}
        </ul>
      </div>

    </div>
  );
};
export default AnalysisResultsPanel;
