import React from 'react';
import ComplaintForm from '../components/complaint/ComplaintForm';
import CopilotPanel from '../components/copilot/CopilotPanel';

export const LogComplaintPage = () => {
  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: 'minmax(0, 1fr) 420px',
      gap: '24px',
      alignItems: 'start'
    }}>
      
      {/* LEFT COLUMN: Structured Customer Complaint Record */}
      <div style={{ minWidth: 0 }}>
        <ComplaintForm />
      </div>

      {/* RIGHT COLUMN: AIVOA Copilot (PDF Upload + Chat + AI Findings) */}
      <div style={{ height: 'calc(100vh - 90px)', position: 'sticky', top: '20px' }}>
        <CopilotPanel />
      </div>

    </div>
  );
};
export default LogComplaintPage;
