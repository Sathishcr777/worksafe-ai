import React from 'react';

interface MetricCardProps {
  label: string;
  value: string | number;
  unit?: string;
  subtext?: string;
  icon?: React.ReactNode;
  statusColor?: 'normal' | 'warning' | 'danger' | 'info' | 'neutral';
  badge?: string;
}

export const MetricCard: React.FC<MetricCardProps> = ({
  label,
  value,
  unit,
  subtext,
  icon,
  statusColor = 'neutral',
  badge
}) => {
  let valueColor = '#f1f5f9';
  let accentBorder = 'var(--border-dim, #1f2738)';

  if (statusColor === 'normal') {
    valueColor = '#34d399';
    accentBorder = 'rgba(16, 185, 129, 0.4)';
  } else if (statusColor === 'warning') {
    valueColor = '#fbbf24';
    accentBorder = 'rgba(245, 158, 11, 0.4)';
  } else if (statusColor === 'danger') {
    valueColor = '#f87171';
    accentBorder = 'rgba(239, 68, 68, 0.4)';
  } else if (statusColor === 'info') {
    valueColor = '#38bdf8';
    accentBorder = 'rgba(56, 189, 248, 0.4)';
  }

  return (
    <div
      style={{
        backgroundColor: 'var(--bg-card, #11151f)',
        border: '1px solid var(--border-dim, #1f2738)',
        borderTop: `2px solid ${accentBorder}`,
        borderRadius: '6px',
        padding: '14px 16px',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        gap: '8px',
        minWidth: '130px',
        position: 'relative',
        boxShadow: '0 2px 4px rgba(0, 0, 0, 0.25)'
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <span
          style={{
            color: 'var(--text-secondary, #94a3b8)',
            fontSize: '0.6875rem',
            fontWeight: 600,
            textTransform: 'uppercase',
            letterSpacing: '0.06em'
          }}
        >
          {label}
        </span>
        {icon && <span style={{ color: 'var(--text-muted, #64748b)', opacity: 0.8 }}>{icon}</span>}
      </div>

      <div style={{ display: 'flex', alignItems: 'baseline', gap: '6px' }}>
        <span
          style={{
            fontFamily: 'var(--font-mono, monospace)',
            fontSize: '1.625rem',
            fontWeight: 700,
            color: valueColor,
            lineHeight: 1
          }}
        >
          {value}
        </span>
        {unit && (
          <span
            style={{
              color: 'var(--text-muted, #64748b)',
              fontSize: '0.75rem',
              fontFamily: 'var(--font-mono, monospace)'
            }}
          >
            {unit}
          </span>
        )}
      </div>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        {subtext && (
          <span style={{ color: 'var(--text-muted, #64748b)', fontSize: '0.6875rem' }}>
            {subtext}
          </span>
        )}
        {badge && (
          <span
            style={{
              fontFamily: 'var(--font-mono, monospace)',
              fontSize: '0.625rem',
              fontWeight: 600,
              padding: '1px 5px',
              borderRadius: '3px',
              backgroundColor: 'var(--bg-card-subtle, #161c2b)',
              color: 'var(--text-secondary, #94a3b8)',
              border: '1px solid var(--border-dim, #1f2738)'
            }}
          >
            {badge}
          </span>
        )}
      </div>
    </div>
  );
};
