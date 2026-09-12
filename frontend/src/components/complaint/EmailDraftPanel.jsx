import React, { useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { Mail, Copy, RefreshCw, Trash2, CheckCircle2, AlertCircle, Sparkles } from 'lucide-react';
import {
  generateEmailDraft,
  updateEmailDraft,
  clearEmailDraft
} from '../../store/slices/complaintFormSlice';

export const EmailDraftPanel = () => {
  const dispatch = useDispatch();
  const { emailDraft, fields } = useSelector((state) => state.complaintForm);
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    const fullEmailText = `To: ${emailDraft.to || 'Quality Assurance Team'}\nSubject: ${emailDraft.subject}\n\n${emailDraft.body}`;
    try {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(fullEmailText);
      } else {
        // Fallback for non-secure contexts
        const textArea = document.createElement('textarea');
        textArea.value = fullEmailText;
        document.body.appendChild(textArea);
        textArea.select();
        document.execCommand('copy');
        document.body.removeChild(textArea);
      }
      setCopied(true);
      setTimeout(() => setCopied(false), 2500);
    } catch (err) {
      console.error('Failed to copy email to clipboard:', err);
    }
  };

  const handleRegenerate = () => {
    dispatch(generateEmailDraft());
  };

  const handleClear = () => {
    dispatch(clearEmailDraft());
  };

  return (
    <div
      className="glass-panel"
      id="email-draft-section"
      style={{
        padding: '24px',
        background: '#ffffff',
        border: '1px solid #e2e8f0',
        borderRadius: '8px',
        boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.05)',
        marginBottom: '24px'
      }}
    >
      {/* Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          paddingBottom: '14px',
          marginBottom: '18px',
          borderBottom: '1px solid #e2e8f0'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div
            style={{
              width: '28px',
              height: '28px',
              borderRadius: '6px',
              background: '#e0f2fe',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#0284c7'
            }}
          >
            <Mail size={16} />
          </div>
          <div>
            <h3
              style={{
                fontSize: '0.95rem',
                fontWeight: 700,
                color: '#0f172a',
                textTransform: 'uppercase',
                letterSpacing: '0.04em'
              }}
            >
              EMAIL DRAFT
            </h3>
            <p style={{ fontSize: '0.75rem', color: '#64748b' }}>
              Dynamic QA Notification Draft (Form-Synchronized)
            </p>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {emailDraft.generated && (
            <span
              style={{
                fontSize: '0.72rem',
                fontWeight: 600,
                color: '#0369a1',
                background: '#e0f2fe',
                padding: '3px 10px',
                borderRadius: '12px',
                border: '1px solid #bae6fd'
              }}
            >
              Draft Ready
            </span>
          )}

          {!emailDraft.generated && !emailDraft.isGenerating && (
            <button
              onClick={handleRegenerate}
              className="glass-button-primary"
              style={{
                fontSize: '0.78rem',
                padding: '5px 12px',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px'
              }}
            >
              <Sparkles size={14} /> Generate Email Draft
            </button>
          )}
        </div>
      </div>

      {/* Loading State */}
      {emailDraft.isGenerating && (
        <div
          style={{
            padding: '32px 16px',
            textAlign: 'center',
            color: '#0284c7',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: '8px'
          }}
        >
          <RefreshCw size={22} className="spinning" style={{ animation: 'spin 1s linear infinite' }} />
          <span style={{ fontSize: '0.85rem', fontWeight: 600 }}>
            Generating dynamic QA complaint notification email...
          </span>
          <span style={{ fontSize: '0.75rem', color: '#64748b' }}>
            Synthesizing current batch details and risk findings without hallucination
          </span>
        </div>
      )}

      {/* Empty State / Prompt */}
      {!emailDraft.generated && !emailDraft.isGenerating && (
        <div
          style={{
            padding: '24px',
            background: '#f8fafc',
            border: '1px dashed #cbd5e1',
            borderRadius: '6px',
            textAlign: 'center'
          }}
        >
          <p style={{ fontSize: '0.85rem', color: '#475569', fontWeight: 500, marginBottom: '6px' }}>
            No email draft generated yet.
          </p>
          <p style={{ fontSize: '0.78rem', color: '#64748b', maxWidth: '480px', margin: '0 auto' }}>
            You can ask the AIVOA Copilot on the right (e.g. <em>"Create an email for this complaint"</em>,{' '}
            <em>"Draft an email to QA"</em>, or <em>"Create a Gmail"</em>) or click the{' '}
            <strong>Generate Email Draft</strong> button above.
          </p>
        </div>
      )}

      {/* Active Generated Draft */}
      {emailDraft.generated && !emailDraft.isGenerating && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          {/* TO Field */}
          <div>
            <label
              style={{
                display: 'block',
                fontSize: '0.78rem',
                fontWeight: 600,
                color: '#475569',
                marginBottom: '4px',
                textTransform: 'uppercase',
                letterSpacing: '0.04em'
              }}
            >
              To:
            </label>
            <input
              type="text"
              className="glass-input"
              value={emailDraft.to || ''}
              onChange={(e) => dispatch(updateEmailDraft({ to: e.target.value }))}
              placeholder="Quality Assurance Team"
              style={{ fontSize: '0.85rem', padding: '8px 12px' }}
            />
          </div>

          {/* SUBJECT Field */}
          <div>
            <label
              style={{
                display: 'block',
                fontSize: '0.78rem',
                fontWeight: 600,
                color: '#475569',
                marginBottom: '4px',
                textTransform: 'uppercase',
                letterSpacing: '0.04em'
              }}
            >
              Subject:
            </label>
            <input
              type="text"
              className="glass-input"
              value={emailDraft.subject || ''}
              onChange={(e) => dispatch(updateEmailDraft({ subject: e.target.value }))}
              placeholder="Customer Complaint Notification..."
              style={{ fontSize: '0.85rem', fontWeight: 600, padding: '8px 12px' }}
            />
          </div>

          {/* BODY Field */}
          <div>
            <label
              style={{
                display: 'block',
                fontSize: '0.78rem',
                fontWeight: 600,
                color: '#475569',
                marginBottom: '4px',
                textTransform: 'uppercase',
                letterSpacing: '0.04em'
              }}
            >
              Body:
            </label>
            <textarea
              rows={14}
              className="glass-input"
              value={emailDraft.body || ''}
              onChange={(e) => dispatch(updateEmailDraft({ body: e.target.value }))}
              placeholder="Email body text..."
              style={{
                fontSize: '0.85rem',
                lineHeight: '1.55',
                fontFamily: 'inherit',
                resize: 'vertical',
                padding: '12px'
              }}
            />
          </div>

          {/* Action Buttons Toolbar */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              paddingTop: '12px',
              borderTop: '1px solid #e2e8f0',
              marginTop: '4px'
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <button
                onClick={handleCopy}
                className="glass-button-primary"
                style={{
                  fontSize: '0.82rem',
                  padding: '7px 16px',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '6px',
                  background: copied ? '#16a34a' : undefined
                }}
              >
                {copied ? <CheckCircle2 size={15} /> : <Copy size={15} />}
                {copied ? 'Copied to Clipboard!' : 'Copy Email'}
              </button>

              <button
                onClick={handleRegenerate}
                className="glass-button-secondary"
                title="Regenerate draft using current form values"
                style={{
                  fontSize: '0.82rem',
                  padding: '7px 14px',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '6px'
                }}
              >
                <RefreshCw size={14} /> Regenerate
              </button>
            </div>

            <button
              onClick={handleClear}
              className="glass-button-secondary"
              title="Clear draft"
              style={{
                fontSize: '0.78rem',
                padding: '7px 12px',
                color: '#ef4444',
                borderColor: '#fecaca',
                background: '#fef2f2',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '4px'
              }}
            >
              <Trash2 size={13} /> Clear Draft
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default EmailDraftPanel;
