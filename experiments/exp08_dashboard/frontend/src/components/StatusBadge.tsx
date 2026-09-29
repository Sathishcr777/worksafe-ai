import React from 'react';
import type { SafetyState } from '../types';

interface StatusBadgeProps {
  state: SafetyState | 'READY' | 'DEGRADED' | 'ONLINE' | 'STANDBY' | 'HEALTHY' | string;
  size?: 'sm' | 'md' | 'lg';
  pulse?: boolean;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ state, size = 'md', pulse = false }) => {
  const norm = (state || 'UNKNOWN').toUpperCase();

  let bg = 'rgba(100, 116, 139, 0.16)';
  let border = '#475569';
  let text = '#94a3b8';
  let dotColor = '#64748b';

  if (norm === 'NORMAL' || norm === 'READY' || norm === 'HEALTHY' || norm === 'ONLINE') {
    bg = 'rgba(16, 185, 129, 0.14)';
    border = '#059669';
    text = '#34d399';
    dotColor = '#10b981';
  } else if (norm === 'WARNING') {
    bg = 'rgba(245, 158, 11, 0.16)';
    border = '#d97706';
    text = '#fbbf24';
    dotColor = '#f59e0b';
  } else if (norm === 'DANGER' || norm === 'CRITICAL') {
    bg = 'rgba(239, 68, 68, 0.18)';
    border = '#dc2626';
    text = '#f87171';
    dotColor = '#ef4444';
  } else if (norm === 'RECOVERY') {
    bg = 'rgba(6, 182, 212, 0.16)';
    border = '#0891b2';
    text = '#38bdf8';
    dotColor = '#06b6d4';
  } else if (norm === 'DEGRADED' || norm === 'STANDBY') {
    bg = 'rgba(217, 119, 6, 0.12)';
    border = '#b45309';
    text = '#fcd34d';
    dotColor = '#d97706';
  } else if (norm === 'UNKNOWN') {
    bg = 'rgba(168, 85, 247, 0.18)';
    border = '#9333ea';
    text = '#c084fc';
    dotColor = '#a855f7';
  }

  const padding = size === 'sm' ? '2px 8px' : size === 'lg' ? '6px 14px' : '4px 10px';
  const fontSize = size === 'sm' ? '0.6875rem' : size === 'lg' ? '0.875rem' : '0.75rem';

  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '6px',
        padding,
        borderRadius: '4px',
        border: `1px solid ${border}`,
        backgroundColor: bg,
        color: text,
        fontFamily: 'var(--font-mono, monospace)',
        fontSize,
        fontWeight: 600,
        letterSpacing: '0.04em',
        textTransform: 'uppercase',
        userSelect: 'none',
        whiteSpace: 'nowrap'
      }}
    >
      <span
        style={{
          width: size === 'sm' ? '5px' : '6px',
          height: size === 'sm' ? '5px' : '6px',
          borderRadius: '50%',
          backgroundColor: dotColor,
          boxShadow: pulse ? `0 0 8px ${dotColor}` : 'none',
          animation: pulse ? 'pulse-glow 2s infinite' : 'none'
        }}
      />
      {norm}
    </span>
  );
};
