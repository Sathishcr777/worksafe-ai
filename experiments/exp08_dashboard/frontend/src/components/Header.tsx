import React, { useState, useEffect } from 'react';
import { Shield } from 'lucide-react';
import type { SafetyState } from '../types';
import type { ConnectionState } from '../services/websocket';

interface HeaderProps {
  safetyState: SafetyState;
  connectionState: ConnectionState;
}

export const Header: React.FC<HeaderProps> = ({ safetyState, connectionState }) => {
  const [currentTime, setCurrentTime] = useState<string>(new Date().toUTCString());

  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTime(new Date().toUTCString());
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  return (
    <header className="app-header">
      <div className="header-left">
        <div className="app-logo-badge">
          <Shield size={22} color="#38bdf8" />
          <h1>WorkSafe AI</h1>
          <span className="sub-title">Command Center</span>
        </div>
        <div style={{ color: 'var(--text-muted)', fontSize: '0.75rem', fontFamily: 'var(--font-mono)' }}>
          FACILITY: BAY 01 | MONITORED PLANE: CALIBRATED FLOOR
        </div>
      </div>

      <div className="header-center">
        <div className={`master-state-pill state-${safetyState}`}>
          <div className="state-indicator-dot" />
          <span>STATUS: {safetyState}</span>
        </div>
      </div>

      <div className="header-right">
        <div className="mono" style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
          {currentTime}
        </div>
        <div className={`ws-status-badge ws-${connectionState}`}>
          <div className="ws-status-dot" />
          <span>
            {connectionState === 'CONNECTED' && 'WS LIVE'}
            {connectionState === 'RECONNECTING' && 'WS RECONNECTING...'}
            {connectionState === 'DISCONNECTED' && 'WS OFFLINE'}
            {connectionState === 'CONNECTING' && 'WS CONNECTING...'}
          </span>
        </div>
      </div>
    </header>
  );
};
