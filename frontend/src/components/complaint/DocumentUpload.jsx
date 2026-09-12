import React, { useRef } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { UploadCloud, FileText, Sparkles, Send } from 'lucide-react';
import { uploadComplaintDoc, processTextComplaint } from '../../store/slices/complaintFormSlice';
import { addUserMessage } from '../../store/slices/copilotSlice';

const SAMPLE_COMPLAINT = "A customer reported that several Metformin 500 mg tablets from batch MET500-KP4821 had broken tablets inside 15 blister packs. The batch was manufactured on 18 March 2026 and expires on 17 March 2029. The complaint was received on 11 September 2026. No patient injury was reported.";

const SAMPLE_COMPLAINT_2 = "St. Jude Pharmacy reported discoloration in 3 bottles of Amoxicillin 250 mg (Batch: AMX-2026-9901, Mfg: 10 Jan 2026, Exp: 09 Jan 2029). Received on 05 August 2026. Material: Finished Product. Customer: Dr. Robert Vance.";

export const DocumentUpload = () => {
  const dispatch = useDispatch();
  const fileInputRef = useRef(null);
  const { status, documentName } = useSelector((state) => state.complaintForm);
  const [textInput, setTextInput] = React.useState('');

  const handleFileChange = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      dispatch(uploadComplaintDoc(file));
    }
  };

  const handleProcessText = (textToProcess) => {
    const query = textToProcess || textInput;
    if (!query.trim()) return;
    dispatch(processTextComplaint(query));
    dispatch(addUserMessage(query));
    if (!textToProcess) setTextInput('');
  };

  return (
    <div className="glass-panel" style={{ padding: '24px', marginBottom: '24px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
        <h3 style={{ fontSize: '1.05rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Sparkles size={18} color="var(--primary-cyan)" />
          Provide Unstructured Complaint Input
        </h3>
        {documentName && (
          <span style={{ fontSize: '0.8rem', color: 'var(--text-highlight)', background: 'rgba(0, 212, 255, 0.1)', padding: '4px 10px', borderRadius: '12px' }}>
            Loaded: {documentName}
          </span>
        )}
      </div>

      {/* File Dropzone */}
      <div
        onClick={() => fileInputRef.current?.click()}
        style={{
          border: '2px dashed var(--border-glow)',
          borderRadius: 'var(--radius-md)',
          padding: '24px',
          textAlign: 'center',
          cursor: 'pointer',
          background: 'rgba(255, 255, 255, 0.01)',
          transition: 'all 0.2s ease',
          marginBottom: '18px'
        }}
      >
        <input
          type="file"
          ref={fileInputRef}
          onChange={handleFileChange}
          accept=".pdf,.docx,.doc,.txt"
          style={{ display: 'none' }}
        />
        <UploadCloud size={36} color="var(--primary-cyan)" style={{ marginBottom: '8px' }} />
        <p style={{ fontWeight: 500, fontSize: '0.95rem', marginBottom: '4px' }}>
          Click or drop PDF / DOCX / TXT complaint document here
        </p>
        <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
          AI will automatically extract fields and analyze compliance risk
        </p>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', margin: '16px 0' }}>
        <div style={{ flex: 1, height: '1px', background: 'var(--border-glass)' }}></div>
        <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>OR PASTE COMPLAINT TEXT</span>
        <div style={{ flex: 1, height: '1px', background: 'var(--border-glass)' }}></div>
      </div>

      {/* Text Area Input */}
      <div style={{ position: 'relative' }}>
        <textarea
          rows={3}
          value={textInput}
          onChange={(e) => setTextInput(e.target.value)}
          placeholder="Paste or type customer complaint narrative here..."
          className="glass-input"
          style={{ resize: 'vertical', width: '100%', paddingRight: '120px' }}
        />
        <button
          onClick={() => handleProcessText()}
          disabled={status === 'analyzing' || !textInput.trim()}
          className="glass-button-primary"
          style={{ position: 'absolute', right: '10px', bottom: '14px', padding: '6px 14px', fontSize: '0.85rem' }}
        >
          {status === 'analyzing' ? 'Analyzing...' : <><Send size={14} /> Process</>}
        </button>
      </div>

      {/* Sample Quick Load Buttons */}
      <div style={{ marginTop: '14px', display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
        <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>Quick Load Demos:</span>
        <button
          onClick={() => handleProcessText(SAMPLE_COMPLAINT)}
          className="glass-button-secondary"
          style={{ fontSize: '0.78rem', padding: '4px 10px', borderRadius: '12px' }}
        >
          <FileText size={13} style={{ marginRight: '4px' }} /> Sample 1 (Metformin 500mg)
        </button>
        <button
          onClick={() => handleProcessText(SAMPLE_COMPLAINT_2)}
          className="glass-button-secondary"
          style={{ fontSize: '0.78rem', padding: '4px 10px', borderRadius: '12px' }}
        >
          <FileText size={13} style={{ marginRight: '4px' }} /> Sample 2 (Amoxicillin 250mg)
        </button>
      </div>
    </div>
  );
};
export default DocumentUpload;
