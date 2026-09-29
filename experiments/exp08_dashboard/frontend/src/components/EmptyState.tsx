import React from 'react';
import { ShieldCheck, SearchX } from 'lucide-react';

interface EmptyStateProps {
  title: string;
  description: string;
  icon?: 'shield' | 'search' | 'custom';
  customIcon?: React.ReactNode;
  action?: {
    label: string;
    onClick: () => void;
  };
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  title,
  description,
  icon = 'shield',
  customIcon,
  action
}) => {
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '48px 24px',
        textAlign: 'center',
        backgroundColor: 'var(--bg-card, #11151f)',
        border: '1px dashed var(--border-dim, #1f2738)',
        borderRadius: '6px',
        color: 'var(--text-secondary, #94a3b8)',
        gap: '12px'
      }}
    >
      <div
        style={{
          width: '48px',
          height: '48px',
          borderRadius: '50%',
          backgroundColor: 'var(--bg-card-subtle, #161c2b)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: 'var(--text-muted, #64748b)'
        }}
      >
        {customIcon ? (
          customIcon
        ) : icon === 'search' ? (
          <SearchX size={24} />
        ) : (
          <ShieldCheck size={24} color="#10b981" />
        )}
      </div>

      <div style={{ maxWidth: '380px' }}>
        <h4
          style={{
            fontSize: '0.9375rem',
            fontWeight: 600,
            color: 'var(--text-primary, #f1f5f9)',
            marginBottom: '4px'
          }}
        >
          {title}
        </h4>
        <p style={{ fontSize: '0.8125rem', color: 'var(--text-muted, #64748b)', lineHeight: 1.4 }}>
          {description}
        </p>
      </div>

      {action && (
        <button
          onClick={action.onClick}
          style={{
            marginTop: '8px',
            padding: '6px 14px',
            borderRadius: '4px',
            backgroundColor: 'var(--bg-card-hover, #1c2336)',
            border: '1px solid var(--border-mid, #2d374d)',
            color: 'var(--text-primary, #f1f5f9)',
            fontSize: '0.8125rem',
            fontWeight: 500,
            cursor: 'pointer'
          }}
        >
          {action.label}
        </button>
      )}
    </div>
  );
};
