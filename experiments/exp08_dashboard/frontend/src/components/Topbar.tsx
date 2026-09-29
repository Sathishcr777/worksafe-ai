import React, { useState, useEffect } from 'react';
import { Radio, Bell, User, Clock, Shield, Keyboard, AlertOctagon } from 'lucide-react';
import type { SafetyState } from '../types';
import type { ConnectionState } from '../services/websocket';

interface TopbarProps {
  safetyState: SafetyState;
  connectionState: ConnectionState;
  activeAlertCount: number;
  onOpenAlerts: () => void;
  onOpenShortcuts?: () => void;
  systemStatus?: 'READY' | 'DEGRADED' | 'UNKNOWN';
  pageTitle?: string;
  pageSubtitle?: string;
}

export const Topbar: React.FC<TopbarProps> = ({
  safetyState,
  connectionState,
  activeAlertCount,
  onOpenAlerts,
  onOpenShortcuts,
  pageTitle = 'COMMAND CENTER',
  pageSubtitle = 'Real-time safety operations & supervisory oversight'
}) => {
  const [timeStr, setTimeStr] = useState('');

  useEffect(() => {
    const update = () => {
      const now = new Date();
      setTimeStr(
        now.toLocaleTimeString('en-US', {
          hour12: false,
          hour: '2-digit',
          minute: '2-digit',
          second: '2-digit'
        }) + ' UTC'
      );
    };
    update();
    const interval = setInterval(update, 1000);
    return () => clearInterval(interval);
  }, []);

  // Format dynamic status badge
  let statusColor = '#10b981';
  let statusBg = 'rgba(16, 185, 129, 0.12)';
  let statusBorder = '#059669';
  let statusText = 'SYSTEM NORMAL';

  if (safetyState === 'WARNING') {
    statusColor = '#f59e0b';
    statusBg = 'rgba(245, 158, 11, 0.14)';
    statusBorder = '#d97706';
    statusText = 'SYSTEM WARNING';
  } else if (safetyState === 'DANGER') {
    statusColor = '#ef4444';
    statusBg = 'rgba(239, 68, 68, 0.16)';
    statusBorder = '#dc2626';
    statusText = 'SYSTEM DANGER';
  } else if (safetyState === 'RECOVERY') {
    statusColor = '#06b6d4';
    statusBg = 'rgba(6, 182, 212, 0.14)';
    statusBorder = '#0891b2';
    statusText = 'SYSTEM RECOVERY';
  } else if (safetyState === 'UNKNOWN') {
    statusColor = '#a855f7';
    statusBg = 'rgba(168, 85, 247, 0.18)';
    statusBorder = '#9333ea';
    statusText = 'SYSTEM UNKNOWN';
  }

  return (
    <header
      style={{
        height: '50px',
        minHeight: '50px',
        backgroundColor: '#070a10',
        borderBottom: '1px solid #161e2e',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 16px',
        userSelect: 'none',
        zIndex: 9
      }}
    >
      {/* Left: Brand / Section Title */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            backgroundColor: '#0c1018',
            padding: '3px 8px',
            borderRadius: '4px',
            border: '1px solid #1a2233'
          }}
        >
          <Shield size={13} color="#10b981" />
          <span style={{ fontSize: '0.6875rem', fontWeight: 700, letterSpacing: '0.06em', color: '#f8fafc' }}>
            WORKSAFE AI
          </span>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column' }}>
          <div
            style={{
              fontSize: '0.8125rem',
              fontWeight: 700,
              letterSpacing: '0.04em',
              color: '#f8fafc',
              lineHeight: 1.1
            }}
          >
            {pageTitle}
          </div>
          <div
            style={{
              fontSize: '0.625rem',
              color: '#64748b',
              marginTop: '1px'
            }}
          >
            {pageSubtitle}
          </div>
        </div>
      </div>

      {/* Center: Facility, Plane & Dynamic Status */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.75rem' }}>
          <span style={{ color: '#64748b', textTransform: 'uppercase', fontSize: '0.65rem' }}>Facility:</span>
          <strong style={{ color: '#e2e8f0', letterSpacing: '0.02em', fontSize: '0.75rem' }}>BAY 01</strong>

          <span style={{ color: '#334155' }}>|</span>

          <span style={{ color: '#64748b', textTransform: 'uppercase', fontSize: '0.65rem' }}>Plane:</span>
          <strong style={{ color: '#38bdf8', letterSpacing: '0.02em', fontSize: '0.75rem' }}>CALIBRATED FLOOR</strong>
        </div>

        {/* Dynamic Status Indicator */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            padding: '3px 10px',
            borderRadius: '4px',
            backgroundColor: statusBg,
            border: `1px solid ${statusBorder}`,
            color: statusColor,
            fontSize: '0.6875rem',
            fontFamily: 'var(--font-mono, monospace)',
            fontWeight: 700,
            letterSpacing: '0.04em'
          }}
        >
          <span
            style={{
              width: '6px',
              height: '6px',
              borderRadius: '50%',
              backgroundColor: statusColor,
              boxShadow: `0 0 8px ${statusColor}`,
              animation: safetyState === 'DANGER' ? 'pulse-glow 1s infinite' : 'none'
            }}
          />
          <span>{statusText}</span>
        </div>

        {safetyState === 'DANGER' && (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              backgroundColor: 'rgba(239, 68, 68, 0.2)',
              border: '1px solid #ef4444',
              borderRadius: '4px',
              padding: '2px 8px',
              color: '#f87171',
              fontSize: '0.6875rem',
              fontWeight: 700,
              animation: 'pulse 1s infinite'
            }}
          >
            <AlertOctagon size={12} color="#ef4444" />
            <span>HAZARD ACTIVE</span>
          </div>
        )}
      </div>

      {/* Right: WS LIVE, Clock, Notification Bell, Shortcuts, Operator Profile */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        {/* WS LIVE Indicator with Latency */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '5px',
            fontSize: '0.6875rem',
            fontFamily: 'var(--font-mono, monospace)',
            fontWeight: 600,
            padding: '3px 8px',
            borderRadius: '4px',
            backgroundColor: '#0c1018',
            border: '1px solid #161e2e',
            color: connectionState === 'CONNECTED' ? '#10b981' : '#f59e0b'
          }}
          title={connectionState === 'CONNECTED' ? 'WebSocket stream synchronized (WAL sync active)' : 'WebSocket disconnected'}
        >
          <Radio size={11} className={connectionState === 'CONNECTED' ? 'spin-pulse' : ''} />
          <span>WS {connectionState === 'CONNECTED' ? 'LIVE (14ms)' : connectionState}</span>
        </div>

        {/* Live Clock */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '5px',
            fontSize: '0.6875rem',
            fontFamily: 'var(--font-mono, monospace)',
            color: '#94a3b8',
            backgroundColor: '#0c1018',
            padding: '3px 8px',
            borderRadius: '4px',
            border: '1px solid #161e2e'
          }}
        >
          <Clock size={11} style={{ color: '#64748b' }} />
          <span>{timeStr}</span>
        </div>

        {/* Keyboard Shortcuts Trigger Button */}
        {onOpenShortcuts && (
          <button
            onClick={onOpenShortcuts}
            title="Keyboard Shortcuts (Press ?)"
            style={{
              background: 'none',
              border: '1px solid #1c2638',
              borderRadius: '4px',
              padding: '4px 7px',
              cursor: 'pointer',
              color: '#94a3b8',
              backgroundColor: '#0c1018',
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              fontSize: '0.6875rem',
              fontFamily: 'var(--font-mono, monospace)'
            }}
          >
            <Keyboard size={13} color="#38bdf8" />
            <kbd className="kbd-badge" style={{ fontSize: '0.625rem', height: '16px', minWidth: '16px', padding: '0 3px' }}>
              ?
            </kbd>
          </button>
        )}

        {/* Notification Bell */}
        <button
          onClick={onOpenAlerts}
          title={`${activeAlertCount} active safety alerts`}
          style={{
            position: 'relative',
            background: 'none',
            border: '1px solid #1c2638',
            borderRadius: '4px',
            padding: '5px 7px',
            cursor: 'pointer',
            color: activeAlertCount > 0 ? '#ef4444' : '#94a3b8',
            backgroundColor: activeAlertCount > 0 ? 'rgba(239, 68, 68, 0.12)' : '#0c1018',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}
        >
          <Bell size={14} />
          {activeAlertCount > 0 && (
            <span
              style={{
                position: 'absolute',
                top: '-4px',
                right: '-4px',
                backgroundColor: '#ef4444',
                color: '#ffffff',
                fontSize: '0.5625rem',
                fontWeight: 700,
                fontFamily: 'var(--font-mono, monospace)',
                padding: '1px 4px',
                borderRadius: '6px',
                lineHeight: 1
              }}
            >
              {activeAlertCount}
            </span>
          )}
        </button>

        {/* Operator Profile */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            fontSize: '0.6875rem',
            color: '#94a3b8',
            backgroundColor: '#0c1018',
            padding: '3px 9px',
            borderRadius: '4px',
            border: '1px solid #161e2e'
          }}
        >
          <User size={12} style={{ color: '#38bdf8' }} />
          <span>OP: <strong style={{ color: '#f8fafc' }}>S. Miller [OP-04]</strong></span>
        </div>
      </div>
    </header>
  );
};
