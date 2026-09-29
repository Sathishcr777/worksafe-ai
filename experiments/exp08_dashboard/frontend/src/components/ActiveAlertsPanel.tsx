import React from 'react';
import { AlertOctagon, CheckCircle2, ShieldAlert, Check } from 'lucide-react';
import type { SafetyEvent } from '../types';

interface ActiveAlertsPanelProps {
  alerts: SafetyEvent[];
  onAcknowledge: (eventId: string) => void;
  onResolve: (eventId: string) => void;
}

export const ActiveAlertsPanel: React.FC<ActiveAlertsPanelProps> = ({
  alerts,
  onAcknowledge,
  onResolve
}) => {
  return (
    <div className="card-panel">
      <div className="card-header">
        <h2>
          <AlertOctagon size={16} color="#ef4444" />
          <span>Active Alerts & Breaches ({alerts.length})</span>
        </h2>
      </div>

      <div className="alerts-list">
        {alerts.length === 0 ? (
          <div
            style={{
              padding: '32px 16px',
              textAlign: 'center',
              color: 'var(--text-muted)',
              fontSize: '0.8125rem'
            }}
          >
            <CheckCircle2 size={32} color="#10b981" style={{ margin: '0 auto 8px', display: 'block' }} />
            <span>All monitored zones nominal. No active safety breaches.</span>
          </div>
        ) : (
          alerts.map((alert) => {
            const isCritical = alert.severity === 'CRITICAL';
            const isAck = alert.lifecycle_status === 'ACKNOWLEDGED';

            return (
              <div key={alert.event_id} className={`alert-card sev-${alert.severity}`}>
                <div className="alert-card-top">
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <ShieldAlert size={16} color={isCritical ? '#ef4444' : '#f59e0b'} />
                    <span className="alert-type" style={{ color: isCritical ? '#ef4444' : '#f59e0b' }}>
                      {alert.event_type}
                    </span>
                  </div>
                  <span
                    className="mono"
                    style={{
                      fontSize: '0.6875rem',
                      padding: '2px 6px',
                      borderRadius: '3px',
                      background: isAck ? 'rgba(56, 189, 248, 0.15)' : 'rgba(239, 68, 68, 0.2)',
                      color: isAck ? '#38bdf8' : '#f87171'
                    }}
                  >
                    {alert.lifecycle_status}
                  </span>
                </div>

                <div className="alert-desc">
                  {alert.description || `Violation detected in ${alert.zone_id || 'zone'}`}
                </div>

                <div className="alert-footer">
                  <span>
                    TRACK: {alert.track_id !== null && alert.track_id !== undefined ? `#${alert.track_id}` : 'SYS'} |{' '}
                    ZONE: {alert.zone_id || 'N/A'}
                  </span>

                  <div style={{ display: 'flex', gap: '6px' }}>
                    {!isAck && (
                      <button
                        className="btn-ack"
                        onClick={() => onAcknowledge(alert.event_id)}
                        title="Acknowledge this active safety violation"
                      >
                        [ACKNOWLEDGE]
                      </button>
                    )}
                    <button
                      className="btn-ack"
                      style={{ background: '#166534', borderColor: '#22c55e' }}
                      onClick={() => onResolve(alert.event_id)}
                      title="Mark violation as resolved"
                    >
                      <Check size={12} style={{ display: 'inline', marginRight: '4px' }} />
                      RESOLVE
                    </button>
                  </div>
                </div>

                {isAck && (
                  <div style={{ fontSize: '0.6875rem', color: '#38bdf8', fontFamily: 'var(--font-mono)' }}>
                    Acked by: {alert.acknowledged_by || 'Operator'}
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
