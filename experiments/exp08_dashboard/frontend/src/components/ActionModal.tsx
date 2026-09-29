import React, { useState } from 'react';
import { AlertTriangle, CheckCircle2, X } from 'lucide-react';

interface ActionModalProps {
  type: 'acknowledge' | 'resolve' | null;
  eventId: string | null;
  onClose: () => void;
  onSubmit: (eventId: string, operator: string, note: string) => Promise<void>;
}

export const ActionModal: React.FC<ActionModalProps> = ({
  type,
  eventId,
  onClose,
  onSubmit
}) => {
  const [operator, setOperator] = useState('Safety_Supervisor_01');
  const [note, setNote] = useState('');
  const [submitting, setSubmitting] = useState(false);

  if (!type || !eventId) return null;

  const isAck = type === 'acknowledge';
  const defaultNote = isAck
    ? 'Verified live feed — worker instructed to exit exclusion zone'
    : 'Worker safely retreated to safe aisle — exclusion zone clear';

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await onSubmit(eventId, operator, note.trim() || defaultNote);
      onClose();
    } catch (err) {
      console.error(`Failed to ${type}:`, err);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(5, 7, 12, 0.8)',
        backdropFilter: 'blur(4px)',
        zIndex: 1100,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '20px'
      }}
      onClick={onClose}
    >
      <div
        style={{
          backgroundColor: 'var(--bg-card, #11151f)',
          border: '1px solid var(--border-mid, #2d374d)',
          borderRadius: '8px',
          width: '100%',
          maxWidth: '460px',
          boxShadow: '0 20px 40px rgba(0, 0, 0, 0.6)',
          overflow: 'hidden'
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <div
          style={{
            padding: '16px 20px',
            borderBottom: '1px solid var(--border-dim, #1f2738)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            backgroundColor: 'var(--bg-card-subtle, #161c2b)'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            {isAck ? (
              <AlertTriangle size={18} color="#f59e0b" />
            ) : (
              <CheckCircle2 size={18} color="#10b981" />
            )}
            <span style={{ fontWeight: 600, color: 'var(--text-primary, #f1f5f9)', fontSize: '0.9375rem' }}>
              {isAck ? 'Acknowledge Safety Alert' : 'Resolve Safety Incident'}
            </span>
          </div>
          <button
            onClick={onClose}
            style={{
              background: 'none',
              border: 'none',
              color: 'var(--text-muted, #64748b)',
              cursor: 'pointer'
            }}
          >
            <X size={16} />
          </button>
        </div>

        <form onSubmit={handleSubmit} style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted, #64748b)', marginBottom: '4px' }}>
              Target Event ID
            </div>
            <div
              style={{
                fontFamily: 'var(--font-mono, monospace)',
                fontSize: '0.8125rem',
                color: 'var(--text-primary, #f1f5f9)',
                backgroundColor: 'var(--bg-app, #090b10)',
                padding: '8px 12px',
                borderRadius: '4px',
                border: '1px solid var(--border-dim, #1f2738)'
              }}
            >
              {eventId}
            </div>
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-secondary, #94a3b8)', marginBottom: '6px' }}>
              Operator / Supervisor Call Sign
            </label>
            <input
              type="text"
              value={operator}
              onChange={(e) => setOperator(e.target.value)}
              required
              style={{
                width: '100%',
                padding: '8px 12px',
                borderRadius: '4px',
                backgroundColor: 'var(--bg-app, #090b10)',
                border: '1px solid var(--border-mid, #2d374d)',
                color: 'var(--text-primary, #f1f5f9)',
                fontSize: '0.8125rem',
                fontFamily: 'inherit',
                outline: 'none'
              }}
            />
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-secondary, #94a3b8)', marginBottom: '6px' }}>
              {isAck ? 'Acknowledgement Note' : 'Resolution Reason & Action Taken'}
            </label>
            <textarea
              value={note}
              placeholder={defaultNote}
              onChange={(e) => setNote(e.target.value)}
              rows={3}
              style={{
                width: '100%',
                padding: '8px 12px',
                borderRadius: '4px',
                backgroundColor: 'var(--bg-app, #090b10)',
                border: '1px solid var(--border-mid, #2d374d)',
                color: 'var(--text-primary, #f1f5f9)',
                fontSize: '0.8125rem',
                fontFamily: 'inherit',
                outline: 'none',
                resize: 'vertical'
              }}
            />
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '8px' }}>
            <button
              type="button"
              onClick={onClose}
              style={{
                padding: '8px 14px',
                borderRadius: '4px',
                backgroundColor: 'transparent',
                border: '1px solid var(--border-mid, #2d374d)',
                color: 'var(--text-secondary, #94a3b8)',
                fontSize: '0.8125rem',
                cursor: 'pointer'
              }}
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              style={{
                padding: '8px 18px',
                borderRadius: '4px',
                backgroundColor: isAck ? '#d97706' : '#059669',
                border: 'none',
                color: '#ffffff',
                fontSize: '0.8125rem',
                fontWeight: 600,
                cursor: submitting ? 'not-allowed' : 'pointer',
                opacity: submitting ? 0.7 : 1
              }}
            >
              {submitting ? 'Updating...' : isAck ? 'Confirm Acknowledge' : 'Confirm Resolution'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
