import React, { useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { updateFormField, clearHighlights, submitComplaintRecord } from '../../store/slices/complaintFormSlice';
import { Save, CheckCircle2, Building, Package, AlertCircle, ShieldCheck } from 'lucide-react';

export const ComplaintForm = () => {
  const dispatch = useDispatch();
  const { fields, highlightMap, status, submitStatus, analysis } = useSelector((state) => state.complaintForm);

  useEffect(() => {
    if (Object.keys(highlightMap).length > 0) {
      const timer = setTimeout(() => {
        dispatch(clearHighlights());
      }, 2500);
      return () => clearTimeout(timer);
    }
  }, [highlightMap, dispatch]);

  const handleChange = (field, value) => {
    dispatch(updateFormField({ field, value }));
  };

  const handleSubmit = () => {
    if (submitStatus === 'submitting' || submitStatus === 'success') return;
    dispatch(submitComplaintRecord());
  };

  const getFieldClass = (fieldKey) => {
    if (highlightMap[fieldKey]) {
      return 'glass-input field-highlight';
    }
    return 'glass-input';
  };

  return (
    <div className="glass-panel" style={{ padding: '24px', background: '#ffffff' }}>
      
      {/* Header */}
      <div style={{ paddingBottom: '16px', marginBottom: '20px', borderBottom: '1px solid #e2e8f0', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div>
          <h2 style={{ fontSize: '1.25rem', color: '#0f172a', fontWeight: 700 }}>Log Customer Complaint</h2>
          <p style={{ fontSize: '0.8rem', color: '#64748b' }}>API & FDF Quality Assurance Module</p>
        </div>
        <span style={{ fontSize: '0.75rem', fontWeight: 600, color: '#0369a1', background: '#e0f2fe', padding: '4px 12px', borderRadius: '12px', border: '1px solid #bae6fd' }}>
          Status: Pending Triage
        </span>
      </div>

      {/* SECTION 1: ORIGIN & CUSTOMER DETAILS */}
      <div style={{ marginBottom: '24px' }}>
        <h3 style={{ fontSize: '0.85rem', textTransform: 'uppercase', letterSpacing: '0.05em', color: '#0369a1', fontWeight: 700, marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '6px' }}>
          <Building size={15} /> SECTION 1: ORIGIN & CUSTOMER DETAILS
        </h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '16px' }}>
          <div>
            <label style={{ display: 'block', fontSize: '0.8rem', color: '#475569', fontWeight: 500, marginBottom: '4px' }}>Complaint Reference</label>
            <input
              type="text"
              className={getFieldClass('complaint_reference')}
              placeholder="e.g. CC-QA-2026-0476"
              value={fields.complaint_reference || fields.complaint_number || ''}
              onChange={(e) => {
                handleChange('complaint_reference', e.target.value);
                handleChange('complaint_number', e.target.value);
              }}
            />
          </div>
          <div>
            <label style={{ display: 'block', fontSize: '0.8rem', color: '#475569', fontWeight: 500, marginBottom: '4px' }}>Complaint Source</label>
            <input
              type="text"
              className={getFieldClass('complaint_source')}
              placeholder="e.g. Healthcare Professional, Pharmacy, Customer"
              value={fields.complaint_source || ''}
              onChange={(e) => handleChange('complaint_source', e.target.value)}
            />
          </div>
          <div>
            <label style={{ display: 'block', fontSize: '0.8rem', color: '#475569', fontWeight: 500, marginBottom: '4px' }}>Customer Name *</label>
            <input
              type="text"
              className={getFieldClass('customer_name')}
              placeholder="Name or identifier of reporting customer"
              value={fields.customer_name || ''}
              onChange={(e) => handleChange('customer_name', e.target.value)}
            />
          </div>
        </div>
      </div>

      {/* SECTION 2: PRODUCT & BATCH IDENTIFICATION */}
      <div style={{ marginBottom: '24px' }}>
        <h3 style={{ fontSize: '0.85rem', textTransform: 'uppercase', letterSpacing: '0.05em', color: '#0369a1', fontWeight: 700, marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '6px' }}>
          <Package size={15} /> SECTION 2: PRODUCT & BATCH IDENTIFICATION
        </h3>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
          <div>
            <label style={{ display: 'block', fontSize: '0.8rem', color: '#475569', fontWeight: 500, marginBottom: '4px' }}>Product Name *</label>
            <input
              type="text"
              className={getFieldClass('product_name')}
              placeholder="Pharmaceutical Product Name"
              value={fields.product_name || ''}
              onChange={(e) => handleChange('product_name', e.target.value)}
            />
          </div>
          <div>
            <label style={{ display: 'block', fontSize: '0.8rem', color: '#475569', fontWeight: 500, marginBottom: '4px' }}>Product Strength / Grade</label>
            <input
              type="text"
              className={getFieldClass('product_strength_grade') || getFieldClass('product_strength')}
              placeholder="e.g. 500 mg, 250 mg, 1 g/vial"
              value={fields.product_strength || fields.product_strength_grade || ''}
              onChange={(e) => {
                handleChange('product_strength_grade', e.target.value);
                handleChange('product_strength', e.target.value);
              }}
            />
          </div>
          <div>
            <label style={{ display: 'block', fontSize: '0.8rem', color: '#475569', fontWeight: 500, marginBottom: '4px' }}>Batch / Lot Number *</label>
            <input
              type="text"
              className={getFieldClass('batch_lot_number')}
              placeholder="e.g. MET500-KP4821, CFT1G-R4516"
              value={fields.batch_lot_number || ''}
              onChange={(e) => handleChange('batch_lot_number', e.target.value)}
            />
          </div>
          <div>
            <label style={{ display: 'block', fontSize: '0.8rem', color: '#475569', fontWeight: 500, marginBottom: '4px' }}>Quantity Affected *</label>
            <input
              type="text"
              className={getFieldClass('affected_quantity')}
              placeholder="e.g. Approximately 20 vials, 50 kg"
              value={fields.affected_quantity || ''}
              onChange={(e) => handleChange('affected_quantity', e.target.value)}
            />
          </div>
          <div>
            <label style={{ display: 'block', fontSize: '0.8rem', color: '#475569', fontWeight: 500, marginBottom: '4px' }}>Manufacturing Date</label>
            <input
              type="date"
              className={getFieldClass('manufacturing_date')}
              value={fields.manufacturing_date || ''}
              onChange={(e) => handleChange('manufacturing_date', e.target.value)}
            />
          </div>
          <div>
            <label style={{ display: 'block', fontSize: '0.8rem', color: '#475569', fontWeight: 500, marginBottom: '4px' }}>Expiry Date</label>
            <input
              type="date"
              className={getFieldClass('expiry_date')}
              value={fields.expiry_date || ''}
              onChange={(e) => handleChange('expiry_date', e.target.value)}
            />
          </div>
          <div>
            <label style={{ display: 'block', fontSize: '0.8rem', color: '#475569', fontWeight: 500, marginBottom: '4px' }}>Manufacturing Site</label>
            <input
              type="text"
              className={getFieldClass('manufacturing_site')}
              placeholder="e.g. Site Alpha - Dublin"
              value={fields.manufacturing_site || ''}
              onChange={(e) => handleChange('manufacturing_site', e.target.value)}
            />
          </div>
          <div>
            <label style={{ display: 'block', fontSize: '0.8rem', color: '#475569', fontWeight: 500, marginBottom: '4px' }}>Material Type</label>
            <input
              type="text"
              className={getFieldClass('material_type')}
              placeholder="e.g. Finished Product, API"
              value={fields.material_type || ''}
              onChange={(e) => handleChange('material_type', e.target.value)}
            />
          </div>
        </div>
      </div>

      {/* SECTION 3: COMPLAINT DETAILS */}
      <div style={{ marginBottom: '24px' }}>
        <h3 style={{ fontSize: '0.85rem', textTransform: 'uppercase', letterSpacing: '0.05em', color: '#0369a1', fontWeight: 700, marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '6px' }}>
          <AlertCircle size={15} /> SECTION 3: COMPLAINT DETAILS
        </h3>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '16px' }}>
          <div>
            <label style={{ display: 'block', fontSize: '0.8rem', color: '#475569', fontWeight: 500, marginBottom: '4px' }}>Complaint Type *</label>
            <input
              type="text"
              className={getFieldClass('complaint_type')}
              placeholder="e.g. Broken Tablets, Packaging Defect"
              value={fields.complaint_type || ''}
              onChange={(e) => handleChange('complaint_type', e.target.value)}
            />
          </div>
          <div>
            <label style={{ display: 'block', fontSize: '0.8rem', color: '#475569', fontWeight: 500, marginBottom: '4px' }}>Complaint Date *</label>
            <input
              type="date"
              className={getFieldClass('complaint_date')}
              value={fields.complaint_date || ''}
              onChange={(e) => handleChange('complaint_date', e.target.value)}
            />
          </div>
        </div>

        <div>
          <label style={{ display: 'block', fontSize: '0.8rem', color: '#475569', fontWeight: 500, marginBottom: '4px' }}>Detailed Complaint Description *</label>
          <textarea
            rows={4}
            className={getFieldClass('complaint_description')}
            placeholder="Provide full narrative description of the customer complaint issue..."
            value={fields.complaint_description || ''}
            onChange={(e) => handleChange('complaint_description', e.target.value)}
            style={{ resize: 'vertical' }}
          />
        </div>
      </div>

      {/* SECTION 4: INITIAL ASSESSMENT & PRIORITY */}
      <div style={{ marginBottom: '24px' }}>
        <h3 style={{ fontSize: '0.85rem', textTransform: 'uppercase', letterSpacing: '0.05em', color: '#0369a1', fontWeight: 700, marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '6px' }}>
          <ShieldCheck size={15} /> SECTION 4: INITIAL ASSESSMENT & PRIORITY
        </h3>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
          <div>
            <label style={{ display: 'block', fontSize: '0.8rem', color: '#475569', fontWeight: 500, marginBottom: '4px' }}>Initial Severity</label>
            <select
              className={getFieldClass('severity_level')}
              value={fields.severity_level || analysis?.risk_assessment?.severity_level || ''}
              onChange={(e) => handleChange('severity_level', e.target.value)}
            >
              <option value="">Select Severity...</option>
              <option value="Low">Low</option>
              <option value="Minor">Minor</option>
              <option value="Major">Major</option>
              <option value="Critical">Critical</option>
            </select>
          </div>
          <div>
            <label style={{ display: 'block', fontSize: '0.8rem', color: '#475569', fontWeight: 500, marginBottom: '4px' }}>Priority</label>
            <select
              className={getFieldClass('priority')}
              value={fields.priority || analysis?.risk_assessment?.priority || ''}
              onChange={(e) => handleChange('priority', e.target.value)}
            >
              <option value="">Select Priority...</option>
              <option value="Low">Low</option>
              <option value="Medium">Medium</option>
              <option value="High">High</option>
              <option value="Urgent">Urgent</option>
            </select>
          </div>
        </div>
      </div>

      {/* Form Submission Action */}
      <div style={{ paddingTop: '16px', borderTop: '1px solid #e2e8f0', display: 'flex', justifyContent: 'flex-end', alignItems: 'center', gap: '12px' }}>
        {submitStatus === 'success' && (
          <span style={{ fontSize: '0.85rem', color: '#16a34a', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '4px' }}>
            <CheckCircle2 size={16} /> Record Saved to Database!
          </span>
        )}
        <button
          onClick={handleSubmit}
          disabled={submitStatus === 'submitting' || submitStatus === 'success' || !fields.product_name || !fields.batch_lot_number}
          className="glass-button-primary"
        >
          <Save size={16} />
          {submitStatus === 'submitting' ? 'Saving Record...' : 'Submit Complaint Record'}
        </button>
      </div>

    </div>
  );
};
export default ComplaintForm;
