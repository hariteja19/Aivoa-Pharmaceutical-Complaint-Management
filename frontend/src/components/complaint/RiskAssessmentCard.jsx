import React from 'react';
import { useSelector } from 'react-redux';
import { ShieldAlert, AlertTriangle, CheckCircle, Info } from 'lucide-react';

export const RiskAssessmentCard = () => {
  const { analysis } = useSelector((state) => state.complaintForm);
  const risk = analysis?.risk_assessment || { severity_level: '', patient_risk_flag: false, rationale: 'Pending AI analysis' };

  const getSeverityBadgeStyle = (severity) => {
    switch (severity) {
      case 'Critical':
        return { bg: 'var(--severity-critical-bg)', color: 'var(--severity-critical)', border: 'rgba(255, 59, 48, 0.4)' };
      case 'Major':
        return { bg: 'var(--severity-major-bg)', color: 'var(--severity-major)', border: 'rgba(255, 149, 0, 0.4)' };
      case 'Minor':
        return { bg: 'var(--severity-minor-bg)', color: 'var(--severity-minor)', border: 'rgba(255, 204, 0, 0.4)' };
      case 'Low':
        return { bg: 'var(--severity-low-bg)', color: 'var(--severity-low)', border: 'rgba(52, 199, 89, 0.4)' };
      default:
        return { bg: 'rgba(148, 163, 184, 0.1)', color: '#64748b', border: 'rgba(148, 163, 184, 0.3)' };
    }
  };

  const style = getSeverityBadgeStyle(risk.severity_level);

  return (
    <div className="glass-panel" style={{ padding: '20px', marginBottom: '24px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
        <h4 style={{ fontSize: '0.95rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <ShieldAlert size={18} color="var(--primary-cyan)" /> AI Risk & Regulatory Severity Assessment
        </h4>
        <span style={{
          background: style.bg,
          color: style.color,
          border: `1px solid ${style.border}`,
          padding: '4px 12px',
          borderRadius: '20px',
          fontWeight: 700,
          fontSize: '0.85rem',
          textTransform: 'uppercase',
          letterSpacing: '0.05em'
        }}>
          {risk.severity_level ? `${risk.severity_level.toUpperCase()} SEVERITY` : 'PENDING EVALUATION'}
        </span>
      </div>

      {/* Patient Risk Alert Flag */}
      {risk.patient_risk_flag && (
        <div style={{ background: 'rgba(255, 59, 48, 0.1)', border: '1px solid rgba(255, 59, 48, 0.3)', padding: '10px 14px', borderRadius: '8px', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '10px' }}>
          <AlertTriangle size={20} color="var(--severity-critical)" />
          <span style={{ fontSize: '0.85rem', color: '#ff6b6b', fontWeight: 600 }}>
            PATIENT SAFETY RISK DETECTED — Expedited Quality Escalation Required under 21 CFR Part 211
          </span>
        </div>
      )}

      {/* Rationale */}
      <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', lineHeight: '1.5' }}>
        <strong>GxP Regulatory Rationale:</strong> {risk.rationale || 'Risk evaluation pending AI workflow processing.'}
      </p>
    </div>
  );
};
export default RiskAssessmentCard;
