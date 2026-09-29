import React, { useState } from 'react';
import { History } from 'lucide-react';
import type { SafetyEvent } from '../types';

interface EventTimelineProps {
  events: SafetyEvent[];
  onAcknowledge: (eventId: string) => void;
}

export const EventTimeline: React.FC<EventTimelineProps> = ({ events, onAcknowledge }) => {
  const [filterSeverity, setFilterSeverity] = useState<string>('ALL');

  const filtered = events.filter((e) => {
    if (filterSeverity === 'ALL') return true;
    return e.severity === filterSeverity;
  });

  return (
    <div className="card-panel">
      <div className="card-header">
        <h2>
          <History size={16} />
          <span>Audit Event Timeline & Log</span>
        </h2>
        <div style={{ display: 'flex', gap: '6px' }}>
          {['ALL', 'CRITICAL', 'WARNING', 'SYSTEM', 'INFO'].map((sev) => (
            <button
              key={sev}
              onClick={() => setFilterSeverity(sev)}
              className="btn-ack"
              style={{
                background: filterSeverity === sev ? '#334155' : 'transparent',
                borderColor: filterSeverity === sev ? '#64748b' : '#334155',
                fontSize: '0.6875rem',
                padding: '2px 8px'
              }}
            >
              {sev}
            </button>
          ))}
        </div>
      </div>

      <div className="events-table-container">
        <table className="events-table">
          <thead>
            <tr>
              <th>TIME (UTC)</th>
              <th>SEVERITY</th>
              <th>EVENT TYPE</th>
              <th>TRACK ID</th>
              <th>ZONE</th>
              <th>STATE</th>
              <th>STATUS</th>
              <th>OPERATOR</th>
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 ? (
              <tr>
                <td colSpan={8} style={{ textAlign: 'center', padding: '24px', color: 'var(--text-muted)' }}>
                  No logged events match current filter.
                </td>
              </tr>
            ) : (
              filtered.map((evt) => {
                const dateStr = new Date(evt.timestamp * 1000).toISOString().substring(11, 19);
                const isAck = evt.lifecycle_status === 'ACKNOWLEDGED';
                const isResolved = evt.lifecycle_status === 'RESOLVED';

                return (
                  <tr key={evt.event_id}>
                    <td style={{ color: 'var(--text-muted)' }}>{dateStr}</td>
                    <td>
                      <span
                        style={{
                          color:
                            evt.severity === 'CRITICAL'
                              ? '#ef4444'
                              : evt.severity === 'WARNING'
                              ? '#f59e0b'
                              : evt.severity === 'SYSTEM'
                              ? '#a855f7'
                              : '#10b981',
                          fontWeight: 700
                        }}
                      >
                        {evt.severity}
                      </span>
                    </td>
                    <td>{evt.event_type}</td>
                    <td>{evt.track_id !== null && evt.track_id !== undefined ? `#${evt.track_id}` : 'SYS'}</td>
                    <td>{evt.zone_id || '—'}</td>
                    <td>{evt.safety_state}</td>
                    <td>
                      <span
                        style={{
                          padding: '1px 5px',
                          borderRadius: '3px',
                          background: isResolved
                            ? 'rgba(16, 185, 129, 0.15)'
                            : isAck
                            ? 'rgba(56, 189, 248, 0.15)'
                            : 'rgba(239, 68, 68, 0.15)',
                          color: isResolved ? '#34d399' : isAck ? '#38bdf8' : '#f87171'
                        }}
                      >
                        {evt.lifecycle_status}
                      </span>
                    </td>
                    <td>
                      {!isAck && !isResolved ? (
                        <button
                          className="btn-ack"
                          style={{ padding: '2px 6px', fontSize: '0.6875rem' }}
                          onClick={() => onAcknowledge(evt.event_id)}
                        >
                          ACK
                        </button>
                      ) : (
                        <span style={{ color: 'var(--text-muted)' }}>
                          {evt.acknowledged_by || evt.resolved_by || '—'}
                        </span>
                      )}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
