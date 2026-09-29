import React from 'react';
import { Server } from 'lucide-react';
import type { SystemHealth } from '../types';

interface SystemHealthPanelProps {
  systemHealth: SystemHealth | null;
}

export const SystemHealthPanel: React.FC<SystemHealthPanelProps> = ({ systemHealth }) => {
  const components = systemHealth?.components || {};
  const env = systemHealth?.environment;

  return (
    <div className="card-panel">
      <div className="card-header">
        <h2>
          <Server size={16} />
          <span>System Pipeline Architecture Readiness</span>
        </h2>
        <span
          className="mono"
          style={{
            fontSize: '0.75rem',
            padding: '2px 8px',
            borderRadius: '4px',
            background: systemHealth?.status === 'READY' ? 'rgba(16, 185, 129, 0.15)' : 'rgba(245, 158, 11, 0.15)',
            color: systemHealth?.status === 'READY' ? '#34d399' : '#fbbf24',
            border: `1px solid ${systemHealth?.status === 'READY' ? '#059669' : '#d97706'}`
          }}
        >
          {systemHealth?.status || 'UNKNOWN'}
        </span>
      </div>

      <div className="readiness-list">
        {Object.entries(components).map(([name, status]) => {
          const isOk = status === 'AVAILABLE' || status === 'HEALTHY';
          return (
            <div key={name} className="readiness-item">
              <span style={{ color: 'var(--text-secondary)' }}>{name}</span>
              <span className={isOk ? 'badge-available' : 'badge-unavailable'}>
                {status}
              </span>
            </div>
          );
        })}
      </div>

      {env && (
        <div
          style={{
            borderTop: '1px solid var(--border-dim)',
            padding: '8px 16px',
            fontSize: '0.6875rem',
            color: 'var(--text-muted)',
            fontFamily: 'var(--font-mono)'
          }}
        >
          HOST: {env.os} | CPU: {env.cpu} | RAM: {env.ram_available_gb}G / {env.ram_total_gb}G | PYTHON: {env.python_version}
        </div>
      )}
    </div>
  );
};
