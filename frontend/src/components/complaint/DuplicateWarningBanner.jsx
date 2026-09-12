import React from 'react';
import { useSelector } from 'react-redux';
import { Copy, AlertCircle } from 'lucide-react';

export const DuplicateWarningBanner = () => {
  const { analysis } = useSelector((state) => state.complaintForm);
  const duplicates = analysis?.duplicates || { is_possible_duplicate: false, match_reasons: [] };

  if (!duplicates.is_possible_duplicate) {
    return null;
  }

  return (
    <div className="glass-panel" style={{ padding: '16px 20px', marginBottom: '24px', borderLeft: '4px solid var(--severity-major)', background: 'rgba(255, 149, 0, 0.08)' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
        <Copy size={20} color="var(--severity-major)" />
        <h4 style={{ fontSize: '0.95rem', color: '#ffb74d', fontWeight: 600 }}>
          Potential Duplicate Complaint Identified
        </h4>
      </div>
      <ul style={{ paddingLeft: '24px', margin: 0 }}>
        {(duplicates.match_reasons || []).map((reason, idx) => (
          <li key={idx} style={{ fontSize: '0.82rem', color: 'var(--text-muted)', marginBottom: '4px' }}>
            {reason}
          </li>
        ))}
      </ul>
    </div>
  );
};
export default DuplicateWarningBanner;
