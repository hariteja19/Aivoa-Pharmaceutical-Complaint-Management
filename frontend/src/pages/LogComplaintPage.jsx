import React from 'react';
import ComplaintForm from '../components/complaint/ComplaintForm';
import DuplicateWarningBanner from '../components/complaint/DuplicateWarningBanner';
import RiskAssessmentCard from '../components/complaint/RiskAssessmentCard';
import AnalysisResultsPanel from '../components/complaint/AnalysisResultsPanel';
import EmailDraftPanel from '../components/complaint/EmailDraftPanel';
import CopilotPanel from '../components/copilot/CopilotPanel';

export const LogComplaintPage = () => {
  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: 'minmax(0, 1fr) 420px',
        gap: '24px',
        alignItems: 'start'
      }}
    >
      {/* LEFT COLUMN: Structured Complaint Details -> AI Analysis -> Email Draft */}
      <div style={{ minWidth: 0, display: 'flex', flexDirection: 'column', gap: '20px' }}>
        {/* 1. Complaint Details Form */}
        <ComplaintForm />

        {/* 2. Initial Assessment / AI Analysis */}
        <DuplicateWarningBanner />
        <RiskAssessmentCard />
        <AnalysisResultsPanel />

        {/* 3. EMAIL DRAFT */}
        <EmailDraftPanel />
      </div>

      {/* RIGHT COLUMN: AIVOA Copilot (PDF Ingestion + Conversational Chat) */}
      <div style={{ height: 'calc(100vh - 90px)', position: 'sticky', top: '20px' }}>
        <CopilotPanel />
      </div>
    </div>
  );
};

export default LogComplaintPage;
