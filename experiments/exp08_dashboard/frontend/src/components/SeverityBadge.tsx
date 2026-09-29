import React from 'react';
import type { EventSeverity } from '../types';

interface SeverityBadgeProps {
  severity: EventSeverity | string;
  size?: 'sm' | 'md';
}

export const SeverityBadge: React.FC<SeverityBadgeProps> = ({ severity, size = 'md' }) => {
  const sev = (severity || 'INFO').toUpperCase();

  let bg = 'rgba(71, 85, 105, 0.2)';
  let border = '#334155';
  let text = '#94a3b8';

  if (sev === 'CRITICAL') {
    bg = 'rgba(239, 68, 68, 0.2)';
    border = '#dc2626';
    text = '#f87171';
  } else if (sev === 'WARNING') {
    bg = 'rgba(245, 158, 11, 0.2)';
    border = '#d97706';
    text = '#fbbf24';
  } else if (sev === 'SYSTEM') {
    bg = 'rgba(168, 85, 247, 0.2)';
    border = '#9333ea';
    text = '#c084fc';
  } else if (sev === 'INFO') {
    bg = 'rgba(56, 189, 248, 0.15)';
    border = '#0284c7';
    text = '#38bdf8';
  }

  const padding = size === 'sm' ? '1px 6px' : '3px 8px';
  const fontSize = size === 'sm' ? '0.625rem' : '0.6875rem';

  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        padding,
        borderRadius: '3px',
        border: `1px solid ${border}`,
        backgroundColor: bg,
        color: text,
        fontFamily: 'var(--font-mono, monospace)',
        fontSize,
        fontWeight: 700,
        letterSpacing: '0.05em',
        textTransform: 'uppercase',
        userSelect: 'none',
        whiteSpace: 'nowrap'
      }}
    >
      {sev}
    </span>
  );
};
