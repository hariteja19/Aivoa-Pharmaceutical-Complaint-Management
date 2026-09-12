import React, { useEffect, useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { fetchComplaintsList, setFilterSearch, setFilterSeverity, deleteComplaint } from '../store/slices/complaintsListSlice';
import { Search, ChevronRight, X, Trash2, AlertTriangle } from 'lucide-react';

const parseCapaRecommendations = (capa) => {
  if (!capa) return [];
  if (Array.isArray(capa)) return capa;
  if (typeof capa === 'string') {
    try {
      const parsed = JSON.parse(capa);
      if (Array.isArray(parsed)) return parsed;
      return [capa];
    } catch {
      return [capa];
    }
  }
  return [];
};

export const ComplaintsListPage = () => {
  const dispatch = useDispatch();
  const { items, total, status, filters } = useSelector((state) => state.complaintsList);
  const [selectedRecord, setSelectedRecord] = useState(null);
  // Fix 4: delete confirmation state
  const [deleteTarget, setDeleteTarget] = useState(null); // { id, complaint_number }
  const [isDeleting, setIsDeleting] = useState(false);

  // Fix 2: Always re-fetch on mount (covers tab-switch after Copilot submit) AND on filter change
  useEffect(() => {
    dispatch(fetchComplaintsList({ search: filters.search, severity: filters.severity }));
  }, [dispatch, filters.search, filters.severity]);

  // Fix 5: Search only updates filter — does NOT open any record
  const handleSearchChange = (e) => {
    dispatch(setFilterSearch(e.target.value));
  };

  // Fix 5: Prevent Enter key in search from doing anything unexpected
  const handleSearchKeyDown = (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
    }
  };

  const handleSeverityFilter = (sev) => {
    dispatch(setFilterSeverity(sev));
  };

  // Fix 4: Delete confirmation + API call
  const handleDeleteConfirm = async () => {
    if (!deleteTarget) return;
    setIsDeleting(true);
    try {
      await dispatch(deleteComplaint(deleteTarget.id));
      setDeleteTarget(null);
      // If the deleted record was open in the modal, close it
      if (selectedRecord && selectedRecord.id === deleteTarget.id) {
        setSelectedRecord(null);
      }
    } finally {
      setIsDeleting(false);
    }
  };

  const getSeverityBadgeClass = (sev) => {
    switch (sev) {
      case 'Critical': return { color: '#dc2626', bg: '#fef2f2', border: '#fecaca' };
      case 'Major': return { color: '#d97706', bg: '#fffbeb', border: '#fde68a' };
      case 'Minor': return { color: '#ca8a04', bg: '#fefce8', border: '#fef08a' };
      default: return { color: '#16a34a', bg: '#f0fdf4', border: '#bbf7d0' };
    }
  };

  return (
    <div className="glass-panel" style={{ padding: '24px', background: '#ffffff' }}>
      
      {/* Header & Controls */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <h2 style={{ fontSize: '1.25rem', fontWeight: 700, color: '#0f172a' }}>Pharmaceutical Complaints Directory</h2>
          <p style={{ fontSize: '0.8rem', color: '#64748b' }}>
            Showing {items.length} of {total} stored GxP complaint audit records
          </p>
        </div>

        <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
          {/* Fix 5: Search box — pure filter, no auto-open */}
          <div style={{ position: 'relative', minWidth: '240px' }}>
            <Search size={15} color="#94a3b8" style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)' }} />
            <input
              type="text"
              placeholder="Search product, batch, customer..."
              value={filters.search}
              onChange={handleSearchChange}
              onKeyDown={handleSearchKeyDown}
              className="glass-input"
              style={{ paddingLeft: '34px', fontSize: '0.84rem' }}
            />
          </div>

          {/* Severity Filter Pills */}
          <div style={{ display: 'flex', gap: '4px' }}>
            {['ALL', 'Critical', 'Major', 'Minor', 'Low'].map((s) => (
              <button
                key={s}
                onClick={() => handleSeverityFilter(s)}
                className={filters.severity === s ? 'glass-button-primary' : 'glass-button-secondary'}
                style={{ fontSize: '0.78rem', padding: '5px 10px' }}
              >
                {s}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Complaints Table */}
      {status === 'loading' ? (
        <div style={{ padding: '40px', textAlign: 'center', color: '#64748b' }}>
          Loading records from database...
        </div>
      ) : items.length === 0 ? (
        <div style={{ padding: '40px', textAlign: 'center', color: '#64748b', border: '1px dashed #cbd5e1', borderRadius: '8px' }}>
          No complaint records found in database. Log a new complaint to get started!
        </div>
      ) : (
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.86rem' }}>
            <thead>
              <tr style={{ borderBottom: '2px solid #e2e8f0', color: '#475569', textAlign: 'left', background: '#f8fafc' }}>
                <th style={{ padding: '10px 12px' }}>Complaint #</th>
                <th style={{ padding: '10px 12px' }}>Product</th>
                <th style={{ padding: '10px 12px' }}>Batch / Lot</th>
                <th style={{ padding: '10px 12px' }}>Customer</th>
                <th style={{ padding: '10px 12px' }}>Date</th>
                <th style={{ padding: '10px 12px' }}>Severity</th>
                <th style={{ padding: '10px 12px' }}>Status</th>
                {/* Fix 4: Actions column now has View + Delete */}
                <th style={{ padding: '10px 12px', textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {items.map((row) => {
                const sStyle = getSeverityBadgeClass(row.severity_level);
                return (
                  // Fix 5: Removed onClick from <tr> — opening is ONLY via View button
                  <tr
                    key={row.id}
                    style={{ borderBottom: '1px solid #f1f5f9' }}
                  >
                    <td style={{ padding: '12px', fontWeight: 700, color: '#0284c7' }}>{row.complaint_reference || row.complaint_number}</td>
                    <td style={{ padding: '12px', fontWeight: 500, color: '#0f172a' }}>{row.product_name} {row.product_strength_grade || row.product_strength || ''}</td>
                    <td style={{ padding: '12px', fontFamily: 'monospace', color: '#334155' }}>{row.batch_lot_number}</td>
                    <td style={{ padding: '12px', color: '#64748b' }}>{row.customer_name || 'N/A'}</td>
                    <td style={{ padding: '12px', color: '#334155' }}>{row.complaint_date}</td>
                    <td style={{ padding: '12px' }}>
                      <span style={{ background: sStyle.bg, color: sStyle.color, border: `1px solid ${sStyle.border}`, padding: '2px 8px', borderRadius: '10px', fontSize: '0.75rem', fontWeight: 600 }}>
                        {row.severity_level || 'Minor'}
                      </span>
                    </td>
                    <td style={{ padding: '12px' }}>
                      <span style={{ color: '#0369a1', fontSize: '0.8rem', fontWeight: 500 }}>{row.status}</span>
                    </td>
                    <td style={{ padding: '12px', textAlign: 'right' }}>
                      <div style={{ display: 'inline-flex', gap: '6px' }}>
                        {/* Fix 5: View button is the ONLY trigger for opening the modal */}
                        <button
                          className="glass-button-secondary"
                          style={{ padding: '4px 8px', fontSize: '0.75rem' }}
                          onClick={() => setSelectedRecord(row)}
                        >
                          View <ChevronRight size={12} />
                        </button>
                        {/* Fix 4: Delete button triggers confirmation */}
                        <button
                          className="glass-button-secondary"
                          style={{ padding: '4px 8px', fontSize: '0.75rem', color: '#dc2626', borderColor: '#fecaca' }}
                          onClick={() => setDeleteTarget({ id: row.id, complaint_number: row.complaint_reference || row.complaint_number })}
                          title="Delete complaint"
                        >
                          <Trash2 size={12} />
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Fix 4: Delete Confirmation Dialog */}
      {deleteTarget && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(15, 23, 42, 0.5)', backdropFilter: 'blur(4px)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1100, padding: '20px' }}>
          <div style={{ background: '#ffffff', border: '1px solid #fecaca', borderRadius: '12px', maxWidth: '420px', width: '100%', padding: '28px', boxShadow: '0 20px 25px -5px rgba(0,0,0,0.15)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
              <AlertTriangle size={24} color="#dc2626" />
              <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: '#0f172a' }}>Confirm Deletion</h3>
            </div>
            <p style={{ fontSize: '0.9rem', color: '#334155', marginBottom: '8px' }}>
              Are you sure you want to permanently delete complaint record:
            </p>
            <p style={{ fontSize: '0.95rem', fontWeight: 700, color: '#0284c7', marginBottom: '20px', background: '#f0f9ff', padding: '8px 12px', borderRadius: '6px' }}>
              {deleteTarget.complaint_number}
            </p>
            <p style={{ fontSize: '0.8rem', color: '#64748b', marginBottom: '20px' }}>
              This action cannot be undone. Only this complaint record will be deleted.
            </p>
            <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end' }}>
              <button
                className="glass-button-secondary"
                style={{ padding: '8px 20px' }}
                onClick={() => setDeleteTarget(null)}
                disabled={isDeleting}
              >
                Cancel
              </button>
              <button
                className="glass-button-primary"
                style={{ padding: '8px 20px', background: '#dc2626', borderColor: '#dc2626' }}
                onClick={handleDeleteConfirm}
                disabled={isDeleting}
              >
                {isDeleting ? 'Deleting...' : 'Delete'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Record Detail Modal — Fix 5: only opened via View button, not row click */}
      {selectedRecord && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(15, 23, 42, 0.5)', backdropFilter: 'blur(4px)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000, padding: '20px' }}>
          <div style={{ background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '12px', maxWidth: '700px', width: '100%', maxHeight: '85vh', overflowY: 'auto', padding: '28px', position: 'relative', boxShadow: '0 20px 25px -5px rgba(0,0,0,0.1)' }}>
            <button
              onClick={() => setSelectedRecord(null)}
              style={{ position: 'absolute', right: '20px', top: '20px', background: 'none', border: 'none', color: '#64748b', cursor: 'pointer' }}
            >
              <X size={20} />
            </button>

            <h3 style={{ fontSize: '1.2rem', color: '#0284c7', fontWeight: 700, marginBottom: '2px' }}>
              Complaint Audit Record: {selectedRecord.complaint_reference || selectedRecord.complaint_number}
            </h3>
            <p style={{ fontSize: '0.8rem', color: '#64748b', marginBottom: '16px' }}>
              Logged on {new Date(selectedRecord.created_at).toLocaleString()}
            </p>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', fontSize: '0.86rem', marginBottom: '16px', background: '#f8fafc', padding: '14px', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
              <div><strong>Product:</strong> {selectedRecord.product_name} ({selectedRecord.product_strength_grade || selectedRecord.product_strength || 'N/A'})</div>
              <div><strong>Batch/Lot:</strong> {selectedRecord.batch_lot_number}</div>
              <div><strong>Customer:</strong> {selectedRecord.customer_name || 'N/A'}</div>
              <div><strong>Affected Qty:</strong> {selectedRecord.affected_quantity || 'N/A'}</div>
              <div><strong>Severity:</strong> {selectedRecord.severity_level || 'Minor'}</div>
              <div><strong>Completeness Score:</strong> {selectedRecord.completeness_score}%</div>
            </div>

            <h4 style={{ fontSize: '0.9rem', color: '#0f172a', fontWeight: 700, marginTop: '16px', marginBottom: '6px' }}>Complaint Description:</h4>
            <p style={{ fontSize: '0.85rem', color: '#334155', background: '#f1f5f9', padding: '12px', borderRadius: '6px', marginBottom: '16px' }}>
              {selectedRecord.complaint_description}
            </p>

            {/* Fix 3: AI Summary displayed if saved */}
            {selectedRecord.executive_summary && (
              <>
                <h4 style={{ fontSize: '0.9rem', color: '#0369a1', fontWeight: 700, marginBottom: '6px' }}>AI Executive Summary:</h4>
                <p style={{ fontSize: '0.85rem', color: '#334155', background: '#e0f2fe', padding: '12px', borderRadius: '6px', marginBottom: '16px' }}>
                  {selectedRecord.executive_summary}
                </p>
              </>
            )}

            {/* Fix 3: CAPA displayed if saved */}
            {parseCapaRecommendations(selectedRecord.capa_recommendations).length > 0 && (
              <>
                <h4 style={{ fontSize: '0.9rem', color: '#16a34a', fontWeight: 700, marginBottom: '6px' }}>CAPA Action Recommendations:</h4>
                <ul style={{ paddingLeft: '20px', fontSize: '0.82rem', color: '#334155' }}>
                  {parseCapaRecommendations(selectedRecord.capa_recommendations).map((c, i) => (
                    <li key={i} style={{ marginBottom: '4px' }}>{c}</li>
                  ))}
                </ul>
              </>
            )}
          </div>
        </div>
      )}

    </div>
  );
};
export default ComplaintsListPage;
