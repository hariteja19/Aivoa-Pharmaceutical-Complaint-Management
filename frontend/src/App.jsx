import React, { useState } from 'react';
import Header from './components/common/Header';
import LogComplaintPage from './pages/LogComplaintPage';
import ComplaintsListPage from './pages/ComplaintsListPage';

export function App() {
  const [activeTab, setActiveTab] = useState('log');

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', background: '#f1f5f9' }}>
      <Header activeTab={activeTab} setActiveTab={setActiveTab} />
      
      <main style={{ flex: 1, padding: '20px 32px 32px 32px', maxWidth: '1600px', width: '100%', margin: '0 auto' }}>
        {activeTab === 'log' ? <LogComplaintPage /> : <ComplaintsListPage />}
      </main>
    </div>
  );
}

export default App;
