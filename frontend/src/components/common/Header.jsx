import React from 'react';
import { Shield, FileText, PlusCircle, List, Activity } from 'lucide-react';

export const Header = ({ activeTab, setActiveTab }) => {
  return (
    <header style={{
      background: '#ffffff',
      borderBottom: '1px solid #e2e8f0',
      padding: '12px 32px',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      boxShadow: '0 1px 2px 0 rgba(0, 0, 0, 0.03)'
    }}>
      {/* Brand & Subtitle */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
        <div style={{
          width: '38px',
          height: '38px',
          borderRadius: '8px',
          background: '#0284c7',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: '#ffffff'
        }}>
          <Shield size={22} />
        </div>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <h1 style={{ fontSize: '1.15rem', color: '#0f172a', fontWeight: 700, letterSpacing: '-0.01em' }}>
              AIVOA Copilot
            </h1>
            <span style={{
              fontSize: '0.7rem',
              fontWeight: 600,
              color: '#0369a1',
              background: '#e0f2fe',
              border: '1px solid #bae6fd',
              padding: '2px 8px',
              borderRadius: '12px',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px'
            }}>
              <Activity size={10} /> Pending Triage
            </span>
          </div>
          <p style={{ fontSize: '0.78rem', color: '#64748b', marginTop: '1px' }}>
            API & FDF Quality Assurance Module • FDA GxP Complaint Intake
          </p>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div style={{ display: 'flex', gap: '8px' }}>
        <button
          onClick={() => setActiveTab('log')}
          className={activeTab === 'log' ? 'glass-button-primary' : 'glass-button-secondary'}
          style={{ fontSize: '0.85rem' }}
        >
          <PlusCircle size={15} /> Log Customer Complaint
        </button>
        <button
          onClick={() => setActiveTab('list')}
          className={activeTab === 'list' ? 'glass-button-primary' : 'glass-button-secondary'}
          style={{ fontSize: '0.85rem' }}
        >
          <List size={15} /> Complaints Directory
        </button>
      </div>
    </header>
  );
};
export default Header;
