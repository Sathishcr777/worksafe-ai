import React from 'react';
import { CheckCircle2, AlertTriangle, Info, X } from 'lucide-react';

export interface ToastMessage {
  id: string;
  type: 'success' | 'warning' | 'error' | 'info';
  title: string;
  message?: string;
}

interface ToastContainerProps {
  toasts: ToastMessage[];
  onDismiss: (id: string) => void;
}

export const ToastContainer: React.FC<ToastContainerProps> = ({ toasts, onDismiss }) => {
  if (toasts.length === 0) return null;

  return (
    <div
      style={{
        position: 'fixed',
        bottom: '24px',
        right: '24px',
        zIndex: 9999,
        display: 'flex',
        flexDirection: 'column',
        gap: '10px',
        maxWidth: '380px',
        width: '100%',
        pointerEvents: 'none'
      }}
    >
      {toasts.map((t) => {
        let border = '#334155';
        let icon = <Info size={18} color="#38bdf8" />;

        if (t.type === 'success') {
          border = '#059669';
          icon = <CheckCircle2 size={18} color="#10b981" />;
        } else if (t.type === 'warning') {
          border = '#d97706';
          icon = <AlertTriangle size={18} color="#f59e0b" />;
        } else if (t.type === 'error') {
          border = '#dc2626';
          icon = <AlertTriangle size={18} color="#ef4444" />;
        }

        return (
          <div
            key={t.id}
            style={{
              pointerEvents: 'auto',
              backgroundColor: 'var(--bg-card, #11151f)',
              border: `1px solid ${border}`,
              borderRadius: '6px',
              padding: '12px 14px',
              display: 'flex',
              alignItems: 'flex-start',
              gap: '12px',
              boxShadow: '0 8px 24px rgba(0, 0, 0, 0.5)',
              animation: 'slide-up 0.25s ease-out'
            }}
          >
            <div style={{ flexShrink: 0, marginTop: '2px' }}>{icon}</div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div
                style={{
                  fontSize: '0.8125rem',
                  fontWeight: 600,
                  color: 'var(--text-primary, #f1f5f9)'
                }}
              >
                {t.title}
              </div>
              {t.message && (
                <div
                  style={{
                    fontSize: '0.75rem',
                    color: 'var(--text-secondary, #94a3b8)',
                    marginTop: '2px'
                  }}
                >
                  {t.message}
                </div>
              )}
            </div>
            <button
              onClick={() => onDismiss(t.id)}
              style={{
                background: 'none',
                border: 'none',
                color: 'var(--text-muted, #64748b)',
                cursor: 'pointer',
                padding: '2px',
                display: 'flex',
                alignItems: 'center'
              }}
            >
              <X size={14} />
            </button>
          </div>
        );
      })}
    </div>
  );
};
