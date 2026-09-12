import React, { useState, useRef, useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { Bot, Send, UploadCloud, Sparkles, RefreshCw, FileText, CheckCircle2, AlertTriangle, ShieldCheck, Copy, Brain, FileCheck } from 'lucide-react';
import { sendCopilotMessage, addUserMessage, clearCopilotChat } from '../../store/slices/copilotSlice';
import { uploadComplaintDoc, processTextComplaint, resetComplaintForm } from '../../store/slices/complaintFormSlice';

const SAMPLE_COMPLAINT = "A customer reported that several Metformin 500 mg tablets from batch MET500-KP4821 had broken tablets inside 15 blister packs. The batch was manufactured on 18 March 2026 and expires on 17 March 2029. The complaint was received on 11 September 2026. No patient injury was reported.";

const SAMPLE_COMPLAINT_2 = "Customer: Green Valley Pharmacy. Product: Amoxicillin Capsules 250 mg. Batch / Lot: AMX250-B6729. Manufacturing Date: 22-May-2026. Expiry Date: 21-May-2029. Complaint Date: 10-Sep-2026. Complaint Type: Packaging / Product Appearance. Narrative: Approximately 8 bottles were affected with discolored capsules inside sealed packaging.";

const renderCopilotMessage = (msg) => {
  const text = msg.text || '';

  // Check if this message represents field updates or risk assessment
  const isUpdate = text.includes("I've updated the complaint record:") ||
                   text.includes("Updated Complaint Fields") ||
                   (msg.updates && Object.keys(msg.updates).length > 0) ||
                   text.includes("•");

  if (!isUpdate && !msg.riskAssessment) {
    return <div style={{ whiteSpace: 'pre-line' }}>{text}</div>;
  }

  // Parse lines from text
  const rawLines = text.split('\n').map(l => l.trim()).filter(Boolean);
  const bulletLines = [];
  const introLines = [];

  for (const line of rawLines) {
    if (line.startsWith('•') || line.startsWith('-') || line.startsWith('*')) {
      bulletLines.push(line.replace(/^[•\-*]\s*/, ''));
    } else if (
      !line.toLowerCase().includes("i've updated the complaint record") &&
      !line.toLowerCase().includes("updated complaint fields")
    ) {
      introLines.push(line);
    }
  }

  // Extract structured field pairs
  const fieldItems = [];
  if (bulletLines.length > 0) {
    bulletLines.forEach((item) => {
      const parts = item.split(/[→:]/);
      if (parts.length >= 2) {
        fieldItems.push({
          label: parts[0].trim(),
          val: parts.slice(1).join(':').trim()
        });
      } else {
        fieldItems.push({ label: '', val: item });
      }
    });
  } else if (msg.updates && Object.keys(msg.updates).length > 0) {
    Object.entries(msg.updates).forEach(([k, v]) => {
      if (v) {
        const label = k.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
        fieldItems.push({ label, val: String(v) });
      }
    });
  }

  const risk = msg.riskAssessment;
  const getRiskClassification = (sev) => {
    if (sev === 'Critical') return 'High (Patient Safety Risk)';
    if (sev === 'Major') return 'High (GxP Quality Impact)';
    if (sev === 'Minor') return 'Medium (Non-Critical Defect)';
    return 'Low (Routine Observation)';
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
      {introLines.length > 0 && (
        <div style={{ color: '#334155', fontSize: '0.82rem', marginBottom: '2px' }}>
          {introLines.join('\n')}
        </div>
      )}

      {fieldItems.length > 0 && (
        <div>
          <div style={{
            fontWeight: 700,
            color: '#0369a1',
            fontSize: '0.84rem',
            marginBottom: '6px',
            display: 'flex',
            alignItems: 'center',
            gap: '6px'
          }}>
            <CheckCircle2 size={14} color="#0284c7" />
            Updated Complaint Fields
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', paddingLeft: '4px' }}>
            {fieldItems.map((f, i) => (
              <div key={i} style={{ fontSize: '0.81rem', display: 'flex', alignItems: 'flex-start', gap: '6px' }}>
                <span style={{ color: '#0284c7', fontWeight: 700 }}>•</span>
                <div>
                  {f.label && <strong style={{ color: '#334155' }}>{f.label}: </strong>}
                  <span style={{ color: '#0f172a' }}>{f.val}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {risk && risk.severity_level && (
        <div style={{
          marginTop: fieldItems.length > 0 ? '4px' : '0',
          paddingTop: fieldItems.length > 0 ? '6px' : '0',
          borderTop: fieldItems.length > 0 ? '1px dashed #e2e8f0' : 'none'
        }}>
          <div style={{
            fontWeight: 700,
            color: '#0284c7',
            fontSize: '0.84rem',
            marginBottom: '6px',
            display: 'flex',
            alignItems: 'center',
            gap: '6px'
          }}>
            <ShieldCheck size={14} color="#0284c7" />
            Risk Assessment
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', paddingLeft: '4px' }}>
            <div style={{ fontSize: '0.81rem', display: 'flex', alignItems: 'flex-start', gap: '6px' }}>
              <span style={{ color: '#0284c7', fontWeight: 700 }}>•</span>
              <div>
                <strong style={{ color: '#334155' }}>AI Risk Classification: </strong>
                <span style={{ color: '#0f172a' }}>{getRiskClassification(risk.severity_level)}</span>
              </div>
            </div>
            <div style={{ fontSize: '0.81rem', display: 'flex', alignItems: 'flex-start', gap: '6px' }}>
              <span style={{ color: '#0284c7', fontWeight: 700 }}>•</span>
              <div>
                <strong style={{ color: '#334155' }}>Initial Severity: </strong>
                <span style={{
                  color: risk.severity_level === 'Critical' ? '#dc2626' : risk.severity_level === 'Major' ? '#d97706' : '#0284c7',
                  fontWeight: 600
                }}>
                  {risk.severity_level}
                </span>
              </div>
            </div>
            <div style={{ fontSize: '0.81rem', display: 'flex', alignItems: 'flex-start', gap: '6px' }}>
              <span style={{ color: '#0284c7', fontWeight: 700 }}>•</span>
              <div>
                <strong style={{ color: '#334155' }}>Priority: </strong>
                <span style={{ color: '#0f172a' }}>{risk.priority || 'Medium'}</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export const CopilotPanel = () => {
  const dispatch = useDispatch();
  const fileInputRef = useRef(null);
  const { messages, isThinking } = useSelector((state) => state.copilot);
  const { status, documentName, analysis } = useSelector((state) => state.complaintForm);
  
  const [chatInput, setChatInput] = useState('');
  const [isDragging, setIsDragging] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isThinking, analysis]);

  const handleFileChange = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      dispatch(uploadComplaintDoc(file));
      dispatch(addUserMessage(`Uploaded file: ${file.name}`));
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    const file = e.dataTransfer?.files?.[0];
    if (file) {
      dispatch(uploadComplaintDoc(file));
      dispatch(addUserMessage(`Uploaded file: ${file.name}`));
    }
  };

  const handleSampleLoad = (text) => {
    dispatch(processTextComplaint(text));
    dispatch(addUserMessage(text));
  };

  const handleSendChat = (textToSend) => {
    const query = textToSend || chatInput;
    if (!query.trim() || isThinking) return;

    dispatch(addUserMessage(query));
    dispatch(sendCopilotMessage({ userMessage: query }));
    if (!textToSend) setChatInput('');
  };

  const handleQuickAction = (actionType) => {
    if (actionType === 'summarize') {
      handleSendChat('Summarize the complaint narrative.');
    } else if (actionType === 'risk') {
      handleSendChat('Assess the risk and severity level.');
    } else if (actionType === 'duplicates') {
      handleSendChat('Check for duplicate complaints in the database.');
    }
  };

  return (
    <aside className="glass-panel" style={{ height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden', background: '#ffffff' }}>
      
      {/* Copilot Header */}
      <div style={{ padding: '16px 20px', borderBottom: '1px solid #e2e8f0', background: '#f8fafc', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div style={{
            width: '32px',
            height: '32px',
            borderRadius: '6px',
            background: '#0284c7',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#ffffff'
          }}>
            <Bot size={18} />
          </div>
          <div>
            <h3 style={{ fontSize: '1rem', fontWeight: 700, color: '#0f172a' }}>AIVOA Copilot</h3>
            <p style={{ fontSize: '0.75rem', color: '#64748b' }}>Drop complaint files or paste text below.</p>
          </div>
        </div>

        <button
          onClick={() => {
            dispatch(clearCopilotChat());
            dispatch(resetComplaintForm());
          }}
          title="Reset Copilot Session"
          style={{ background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer', padding: '4px' }}
        >
          <RefreshCw size={15} />
        </button>
      </div>

      {/* Top Document Upload Section */}
      <div style={{ padding: '16px', borderBottom: '1px solid #e2e8f0', background: '#ffffff' }}>
        <div
          onClick={() => fileInputRef.current?.click()}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          style={{
            border: isDragging ? '2px dashed #0284c7' : '2px dashed #cbd5e1',
            borderRadius: '6px',
            padding: '16px',
            textAlign: 'center',
            cursor: 'pointer',
            background: isDragging ? '#e0f2fe' : '#f8fafc',
            transform: isDragging ? 'scale(1.01)' : 'scale(1)',
            transition: 'all 0.2s ease'
          }}
        >
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileChange}
            accept=".pdf,.docx,.doc,.txt,.eml"
            style={{ display: 'none' }}
          />
          <UploadCloud size={28} color={isDragging ? '#0284c7' : '#64748b'} style={{ marginBottom: '4px' }} />
          <p style={{ fontWeight: 600, fontSize: '0.85rem', color: isDragging ? '#0369a1' : '#0f172a', marginBottom: '2px' }}>
            {isDragging ? 'Release to upload complaint document' : 'Drag & drop complaint document here'}
          </p>
          <p style={{ fontSize: '0.75rem', color: '#64748b' }}>
            or click to browse • Supported: PDF, DOCX, TXT, EML
          </p>
        </div>

        {documentName && (
          <div style={{ marginTop: '8px', fontSize: '0.78rem', color: '#0369a1', background: '#e0f2fe', padding: '4px 10px', borderRadius: '4px', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <FileText size={14} /> Uploaded: {documentName}
          </div>
        )}

        {/* Quick Demo Loader Buttons */}
        <div style={{ marginTop: '10px', display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
          <span style={{ fontSize: '0.72rem', color: '#64748b', width: '100%' }}>Quick Demos:</span>
          <button
            onClick={() => handleSampleLoad(SAMPLE_COMPLAINT)}
            className="glass-button-secondary"
            style={{ fontSize: '0.72rem', padding: '3px 8px' }}
          >
            Sample 1 (Metformin)
          </button>
          <button
            onClick={() => handleSampleLoad(SAMPLE_COMPLAINT_2)}
            className="glass-button-secondary"
            style={{ fontSize: '0.72rem', padding: '3px 8px' }}
          >
            Sample 2 (Amoxicillin)
          </button>
        </div>

        {/* AI Quick Action Buttons */}
        <div style={{ marginTop: '10px', display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
          <button
            onClick={() => handleQuickAction('summarize')}
            className="glass-button-secondary"
            style={{ fontSize: '0.72rem', padding: '3px 8px', display: 'inline-flex', alignItems: 'center', gap: '4px' }}
          >
            <FileCheck size={12} /> Summarize
          </button>
          <button
            onClick={() => handleQuickAction('risk')}
            className="glass-button-secondary"
            style={{ fontSize: '0.72rem', padding: '3px 8px', display: 'inline-flex', alignItems: 'center', gap: '4px' }}
          >
            <ShieldCheck size={12} /> Assess Risk
          </button>
          <button
            onClick={() => handleQuickAction('duplicates')}
            className="glass-button-secondary"
            style={{ fontSize: '0.72rem', padding: '3px 8px', display: 'inline-flex', alignItems: 'center', gap: '4px' }}
          >
            <Copy size={12} /> Check Duplicates
          </button>
        </div>
      </div>

      {/* Messages Scroll Area */}
      <div style={{ flex: 1, padding: '16px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '12px', background: '#f8fafc' }}>
        {messages.map((msg) => (
          <div
            key={msg.id}
            style={{
              display: 'flex',
              gap: '8px',
              alignSelf: msg.sender === 'user' ? 'flex-end' : 'flex-start',
              maxWidth: '92%'
            }}
          >
            {msg.sender === 'copilot' && (
              <div style={{
                width: '24px',
                height: '24px',
                borderRadius: '50%',
                background: '#e0f2fe',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#0284c7',
                flexShrink: 0
              }}>
                <Bot size={14} />
              </div>
            )}

            <div>
              <div style={{
                padding: '10px 12px',
                borderRadius: msg.sender === 'user' ? '12px 12px 2px 12px' : '12px 12px 12px 2px',
                background: msg.sender === 'user' ? '#0284c7' : '#ffffff',
                border: msg.sender === 'user' ? 'none' : '1px solid #e2e8f0',
                color: msg.sender === 'user' ? '#ffffff' : '#0f172a',
                fontSize: '0.82rem',
                lineHeight: '1.45',
                boxShadow: msg.sender === 'user' ? 'none' : '0 1px 2px 0 rgba(0,0,0,0.05)',
                whiteSpace: 'pre-line'
              }}>
                {msg.sender === 'copilot' ? renderCopilotMessage(msg) : msg.text}
              </div>
              <span style={{ fontSize: '0.65rem', color: '#94a3b8', marginTop: '2px', display: 'block', textAlign: msg.sender === 'user' ? 'right' : 'left' }}>
                {msg.timestamp}
              </span>
            </div>
          </div>
        ))}

        {/* AI Findings Summary Cards in Copilot Feed */}
        {analysis?.executive_summary && (
          <div style={{ background: '#ffffff', border: '1px solid #bae6fd', borderRadius: '8px', padding: '12px', fontSize: '0.8rem', marginTop: '6px' }}>
            <h4 style={{ fontSize: '0.82rem', color: '#0369a1', fontWeight: 700, marginBottom: '4px', display: 'flex', alignItems: 'center', gap: '4px' }}>
              <FileCheck size={14} /> AI Executive Summary
            </h4>
            <p style={{ color: '#334155', lineHeight: '1.4' }}>{analysis.executive_summary}</p>
          </div>
        )}

        {analysis?.duplicates?.is_possible_duplicate && (
          <div style={{ background: '#fffbeb', border: '1px solid #fde68a', borderRadius: '8px', padding: '10px', fontSize: '0.78rem' }}>
            <span style={{ color: '#d97706', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '4px' }}>
              <AlertTriangle size={14} /> Duplicate Alert
            </span>
            <ul style={{ paddingLeft: '16px', margin: '4px 0 0 0', color: '#92400e' }}>
              {analysis.duplicates.match_reasons.map((r, idx) => (
                <li key={idx}>{r}</li>
              ))}
            </ul>
          </div>
        )}

        {analysis?.capa_recommendations && analysis.capa_recommendations.length > 0 && (
          <div style={{ background: '#f0fdf4', border: '1px solid #bbf7d0', borderRadius: '8px', padding: '10px', fontSize: '0.78rem' }}>
            <span style={{ color: '#16a34a', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '4px' }}>
              <ShieldCheck size={14} /> CAPA Action Recommendations
            </span>
            <ul style={{ paddingLeft: '16px', margin: '4px 0 0 0', color: '#166534' }}>
              {analysis.capa_recommendations.slice(0, 3).map((c, idx) => (
                <li key={idx}>{c}</li>
              ))}
            </ul>
          </div>
        )}

        {isThinking && (
          <div style={{ display: 'flex', gap: '6px', alignItems: 'center', color: '#64748b', fontSize: '0.78rem' }}>
            <Bot size={14} color="#0284c7" /> Copilot is updating fields...
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Chat Input Bar */}
      <div style={{ padding: '12px 16px', borderTop: '1px solid #e2e8f0', background: '#ffffff', display: 'flex', gap: '8px', alignItems: 'flex-end' }}>
        <textarea
          rows={1}
          value={chatInput}
          onChange={(e) => {
            setChatInput(e.target.value);
            e.target.style.height = 'auto';
            e.target.style.height = `${Math.min(e.target.scrollHeight, 120)}px`;
          }}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault();
              handleSendChat();
            }
          }}
          placeholder="Paste complaint or instruct Copilot (Enter to send, Shift+Enter for newline)..."
          className="glass-input"
          style={{
            fontSize: '0.82rem',
            resize: 'none',
            minHeight: '38px',
            maxHeight: '120px',
            overflowY: 'auto',
            padding: '8px 12px',
            lineHeight: '1.4'
          }}
        />
        <button
          onClick={() => handleSendChat()}
          disabled={!chatInput.trim() || isThinking}
          className="glass-button-primary"
          style={{ padding: '9px 12px', height: '38px', flexShrink: 0, display: 'flex', alignItems: 'center', justifyContent: 'center' }}
          title="Send to Copilot"
        >
          <Send size={15} />
        </button>
      </div>

    </aside>
  );
};
export default CopilotPanel;
