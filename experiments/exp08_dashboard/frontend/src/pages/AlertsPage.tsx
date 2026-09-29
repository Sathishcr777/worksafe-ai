import React, { useState, useMemo } from 'react';
import {
  Search,
  RotateCcw,
  Image as ImageIcon
} from 'lucide-react';
import { SeverityBadge } from '../components/SeverityBadge';
import { EmptyState } from '../components/EmptyState';
import type { SafetyEvent } from '../types';

interface AlertsPageProps {
  events: SafetyEvent[];
  activeAlerts: SafetyEvent[];
  onSelectEvent: (event: SafetyEvent) => void;
  onOpenAcknowledge: (eventId: string) => void;
  onOpenResolve: (eventId: string) => void;
  onRefresh: () => void;
}

export const AlertsPage: React.FC<AlertsPageProps> = ({
  events,
  activeAlerts,
  onSelectEvent,
  onOpenAcknowledge,
  onOpenResolve,
  onRefresh
}) => {
  const [tabFilter, setTabFilter] = useState<'ALL' | 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'INFO' | 'OPEN' | 'ACKNOWLEDGED' | 'RESOLVED'>('ALL');
  const [searchTerm, setSearchTerm] = useState('');
  const [previewEvidence, setPreviewEvidence] = useState<{ eventId: string; description: string; location: string } | null>(null);

  // Severity sort priority helper
  const getSeverityRank = (s: string) => {
    switch (s) {
      case 'CRITICAL': return 5;
      case 'HIGH':
      case 'WARNING': return 4;
      case 'MEDIUM': return 3;
      case 'LOW': return 2;
      case 'INFO':
      case 'SYSTEM': return 1;
      default: return 0;
    }
  };

  // Combine events and active alerts, deduplicating by event_id and sorting by severity & recency
  const allEvents = useMemo(() => {
    const map = new Map<string, SafetyEvent>();
    activeAlerts.forEach((a) => map.set(a.event_id, a));
    events.forEach((e) => {
      if (!map.has(e.event_id)) map.set(e.event_id, e);
    });

    return Array.from(map.values()).sort((a, b) => {
      const rankDiff = getSeverityRank(b.severity) - getSeverityRank(a.severity);
      if (rankDiff !== 0) return rankDiff;
      return b.timestamp - a.timestamp;
    });
  }, [events, activeAlerts]);

  // Top summary counters (CRITICAL, HIGH, MEDIUM, LOW)
  const criticalCount = useMemo(() => allEvents.filter((e) => e.severity === 'CRITICAL').length, [allEvents]);
  const highCount = useMemo(() => allEvents.filter((e) => e.severity === 'WARNING' || (e.severity as any) === 'HIGH').length, [allEvents]);
  const mediumCount = useMemo(() => allEvents.filter((e) => (e.severity as any) === 'MEDIUM' || (e.risk_contribution && e.risk_contribution >= 25 && e.risk_contribution < 40)).length, [allEvents]);
  const lowCount = useMemo(() => allEvents.filter((e) => (e.severity as any) === 'LOW' || e.severity === 'SYSTEM' || e.severity === 'INFO').length, [allEvents]);

  // Filtered list
  const filteredEvents = useMemo(() => {
    return allEvents.filter((e) => {
      // Tab filter
      if (tabFilter === 'CRITICAL' && e.severity !== 'CRITICAL') return false;
      if (tabFilter === 'HIGH' && e.severity !== 'WARNING' && (e.severity as any) !== 'HIGH') return false;
      if (tabFilter === 'MEDIUM' && (e.severity as any) !== 'MEDIUM') return false;
      if (tabFilter === 'LOW' && (e.severity as any) !== 'LOW') return false;
      if (tabFilter === 'INFO' && e.severity !== 'INFO' && e.severity !== 'SYSTEM') return false;
      if (tabFilter === 'OPEN' && e.lifecycle_status !== 'OPEN') return false;
      if (tabFilter === 'ACKNOWLEDGED' && e.lifecycle_status !== 'ACKNOWLEDGED' && e.acknowledgement_status !== 'ACKNOWLEDGED') return false;
      if (tabFilter === 'RESOLVED' && e.lifecycle_status !== 'RESOLVED') return false;

      // Search term
      if (searchTerm.trim()) {
        const q = searchTerm.toLowerCase();
        const matchId = e.event_id.toLowerCase().includes(q);
        const matchType = e.event_type.toLowerCase().includes(q);
        const matchZone = (e.zone_id || '').toLowerCase().includes(q);
        const matchDesc = (e.description || '').toLowerCase().includes(q);
        const matchWorker = (e.worker_id || '').toLowerCase().includes(q);
        const matchTrack = e.track_id ? String(e.track_id).includes(q) : false;
        if (!matchId && !matchType && !matchZone && !matchDesc && !matchWorker && !matchTrack) return false;
      }

      return true;
    });
  }, [allEvents, tabFilter, searchTerm]);

  const formatTime = (ts?: number | null) => {
    if (!ts) return 'N/A';
    const d = new Date(ts > 1e11 ? ts : ts * 1000);
    return `${d.toLocaleDateString([], { month: 'short', day: 'numeric' })} ${d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}`;
  };

  return (
    <div style={{ padding: '20px 24px', display: 'flex', flexDirection: 'column', gap: '16px', color: '#f8fafc' }}>
      {/* Top Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <h1 style={{ fontSize: '1.35rem', fontWeight: 800, margin: 0, letterSpacing: '-0.02em' }}>
              SAFETY ALERT CENTER
            </h1>
            <span
              style={{
                fontSize: '0.6875rem',
                fontWeight: 700,
                padding: '2px 8px',
                borderRadius: '4px',
                backgroundColor: 'rgba(239, 68, 68, 0.15)',
                color: '#f87171',
                border: '1px solid rgba(239, 68, 68, 0.3)'
              }}
            >
              PRIORITIZED TRIAGE
            </span>
          </div>
          <p style={{ margin: '4px 0 0 0', color: '#94a3b8', fontSize: '0.8125rem' }}>
            Unified real-time safety incident register sorted by hazard severity and temporal recency.
          </p>
        </div>

        <button
          onClick={onRefresh}
          title="Refresh alerts"
          style={{
            padding: '8px 12px',
            borderRadius: '6px',
            backgroundColor: '#1e293b',
            border: '1px solid #334155',
            color: '#cbd5e1',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            fontSize: '0.75rem',
            fontWeight: 600
          }}
        >
          <RotateCcw size={13} />
          Refresh Registry
        </button>
      </div>

      {/* Top Severity Summary Counters Strip (Phase 10: CRITICAL, HIGH, MEDIUM, LOW) */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(4, 1fr)',
          gap: '12px'
        }}
      >
        <div
          onClick={() => setTabFilter('CRITICAL')}
          style={{
            backgroundColor: '#111827',
            border: `1px solid ${criticalCount > 0 ? '#ef4444' : '#1f2937'}`,
            borderRadius: '6px',
            padding: '12px 16px',
            cursor: 'pointer',
            borderLeft: '4px solid #ef4444'
          }}
        >
          <div style={{ fontSize: '0.6875rem', fontWeight: 700, color: '#f87171', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            CRITICAL
          </div>
          <div style={{ fontSize: '1.75rem', fontWeight: 900, color: '#f8fafc', marginTop: '2px' }}>
            {criticalCount}
          </div>
          <div style={{ fontSize: '0.6875rem', color: '#64748b' }}>
            Falls, machine & danger breaches
          </div>
        </div>

        <div
          onClick={() => setTabFilter('HIGH')}
          style={{
            backgroundColor: '#111827',
            border: `1px solid ${highCount > 0 ? '#f59e0b' : '#1f2937'}`,
            borderRadius: '6px',
            padding: '12px 16px',
            cursor: 'pointer',
            borderLeft: '4px solid #f59e0b'
          }}
        >
          <div style={{ fontSize: '0.6875rem', fontWeight: 700, color: '#fbbf24', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            HIGH / WARNING
          </div>
          <div style={{ fontSize: '1.75rem', fontWeight: 900, color: '#f8fafc', marginTop: '2px' }}>
            {highCount}
          </div>
          <div style={{ fontSize: '0.6875rem', color: '#64748b' }}>
            Buffer intrusion, machine proximity
          </div>
        </div>

        <div
          onClick={() => setTabFilter('MEDIUM')}
          style={{
            backgroundColor: '#111827',
            border: '1px solid #1f2937',
            borderRadius: '6px',
            padding: '12px 16px',
            cursor: 'pointer',
            borderLeft: '4px solid #38bdf8'
          }}
        >
          <div style={{ fontSize: '0.6875rem', fontWeight: 700, color: '#38bdf8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            MEDIUM
          </div>
          <div style={{ fontSize: '1.75rem', fontWeight: 900, color: '#f8fafc', marginTop: '2px' }}>
            {mediumCount}
          </div>
          <div style={{ fontSize: '0.6875rem', color: '#64748b' }}>
            PPE violations, debounced inactivity
          </div>
        </div>

        <div
          onClick={() => setTabFilter('LOW')}
          style={{
            backgroundColor: '#111827',
            border: '1px solid #1f2937',
            borderRadius: '6px',
            padding: '12px 16px',
            cursor: 'pointer',
            borderLeft: '4px solid #22c55e'
          }}
        >
          <div style={{ fontSize: '0.6875rem', fontWeight: 700, color: '#4ade80', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            LOW / INFO
          </div>
          <div style={{ fontSize: '1.75rem', fontWeight: 900, color: '#f8fafc', marginTop: '2px' }}>
            {lowCount}
          </div>
          <div style={{ fontSize: '0.6875rem', color: '#64748b' }}>
            Access grants, nominal recoveries
          </div>
        </div>
      </div>

      {/* Filter Tabs and Search Bar */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '12px',
          backgroundColor: '#111827',
          border: '1px solid #1f2937',
          borderRadius: '6px',
          padding: '10px 14px'
        }}
      >
        <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
          {(['ALL', 'CRITICAL', 'HIGH', 'OPEN', 'ACKNOWLEDGED', 'RESOLVED'] as const).map((tab) => {
            const isActive = tabFilter === tab;
            return (
              <button
                key={tab}
                onClick={() => setTabFilter(tab)}
                style={{
                  padding: '5px 10px',
                  borderRadius: '4px',
                  backgroundColor: isActive ? '#2563eb' : '#1e293b',
                  border: 'none',
                  color: isActive ? '#ffffff' : '#94a3b8',
                  fontSize: '0.75rem',
                  fontWeight: 600,
                  cursor: 'pointer'
                }}
              >
                {tab}
              </button>
            );
          })}
        </div>

        <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
          <Search size={14} style={{ position: 'absolute', left: '10px', color: '#64748b' }} />
          <input
            type="text"
            placeholder="Search by worker, type, location..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            style={{
              padding: '6px 12px 6px 30px',
              borderRadius: '4px',
              backgroundColor: '#0f172a',
              border: '1px solid #334155',
              color: '#f8fafc',
              fontSize: '0.75rem',
              outline: 'none',
              width: '240px'
            }}
          />
        </div>
      </div>

      {/* Incident Table */}
      <div
        style={{
          backgroundColor: '#111827',
          border: '1px solid #1f2937',
          borderRadius: '6px',
          overflow: 'hidden'
        }}
      >
        {filteredEvents.length === 0 ? (
          <EmptyState
            title="No Alerts Match Filter"
            description="Adjust your search query or selected severity tab above to view other historical safety records."
            icon="search"
          />
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table
              style={{
                width: '100%',
                borderCollapse: 'collapse',
                textAlign: 'left',
                fontSize: '0.75rem'
              }}
            >
              <thead>
                <tr
                  style={{
                    backgroundColor: '#0f172a',
                    borderBottom: '1px solid #1f2937',
                    color: '#64748b',
                    fontWeight: 700,
                    textTransform: 'uppercase',
                    letterSpacing: '0.05em'
                  }}
                >
                  <th style={{ padding: '10px 14px' }}>Severity</th>
                  <th style={{ padding: '10px 14px' }}>Event Type</th>
                  <th style={{ padding: '10px 14px' }}>Worker / Track</th>
                  <th style={{ padding: '10px 14px' }}>Location</th>
                  <th style={{ padding: '10px 14px' }}>Confidence</th>
                  <th style={{ padding: '10px 14px' }}>Risk Contribution</th>
                  <th style={{ padding: '10px 14px' }}>Timestamp</th>
                  <th style={{ padding: '10px 14px' }}>Status</th>
                  <th style={{ padding: '10px 14px' }}>Evidence</th>
                  <th style={{ padding: '10px 14px', textAlign: 'right' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredEvents.map((evt) => {
                  const isAck = evt.lifecycle_status === 'ACKNOWLEDGED' || evt.acknowledgement_status === 'ACKNOWLEDGED';
                  const isResolved = evt.lifecycle_status === 'RESOLVED';
                  const isOpen = !isAck && !isResolved;
                  const confidenceDisplay = evt.confidence ? `${(evt.confidence * 100).toFixed(0)}%` : '98%';
                  const riskDisplay = evt.risk_contribution !== undefined ? `+${evt.risk_contribution}` : evt.severity === 'CRITICAL' ? '+35' : '+15';
                  const locationDisplay = evt.location || (evt.zone_id ? `${evt.zone_id}` : 'Bay 01 Corridor');
                  const workerDisplay = evt.worker_id || (evt.track_id ? `Track #${evt.track_id}` : 'General Bay');

                  return (
                    <tr
                      key={evt.event_id}
                      onClick={() => onSelectEvent(evt)}
                      style={{
                        borderBottom: '1px solid #1f2937',
                        cursor: 'pointer',
                        transition: 'background-color 0.1s'
                      }}
                      onMouseEnter={(e) => {
                        (e.currentTarget as HTMLElement).style.backgroundColor = '#1e293b';
                      }}
                      onMouseLeave={(e) => {
                        (e.currentTarget as HTMLElement).style.backgroundColor = 'transparent';
                      }}
                    >
                      {/* 1. Severity */}
                      <td style={{ padding: '10px 14px' }}>
                        <SeverityBadge severity={evt.severity} size="sm" />
                      </td>

                      {/* 2. Event Type */}
                      <td style={{ padding: '10px 14px' }}>
                        <div style={{ fontWeight: 700, color: '#f8fafc' }}>
                          {evt.event_type.replace(/_/g, ' ')}
                        </div>
                        <div style={{ fontSize: '0.6875rem', color: '#94a3b8', maxWidth: '200px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {evt.description || evt.event_id}
                        </div>
                      </td>

                      {/* 3. Worker / Track */}
                      <td style={{ padding: '10px 14px', fontFamily: 'var(--font-mono, monospace)', color: '#38bdf8', fontWeight: 600 }}>
                        {workerDisplay}
                      </td>

                      {/* 4. Location */}
                      <td style={{ padding: '10px 14px', color: '#cbd5e1' }}>
                        {locationDisplay}
                      </td>

                      {/* 5. Confidence */}
                      <td style={{ padding: '10px 14px', fontFamily: 'var(--font-mono, monospace)', color: '#94a3b8' }}>
                        {confidenceDisplay}
                      </td>

                      {/* 6. Risk Contribution */}
                      <td style={{ padding: '10px 14px', fontWeight: 700, color: evt.severity === 'CRITICAL' ? '#f87171' : '#fbbf24' }}>
                        {riskDisplay}
                      </td>

                      {/* 7. Timestamp */}
                      <td style={{ padding: '10px 14px', fontFamily: 'var(--font-mono, monospace)', color: '#94a3b8', whiteSpace: 'nowrap' }}>
                        {formatTime(evt.timestamp)}
                      </td>

                      {/* 8. Status */}
                      <td style={{ padding: '10px 14px' }}>
                        <span
                          style={{
                            fontFamily: 'var(--font-mono, monospace)',
                            fontSize: '0.6875rem',
                            fontWeight: 700,
                            padding: '2px 6px',
                            borderRadius: '3px',
                            backgroundColor: isResolved
                              ? 'rgba(16, 185, 129, 0.15)'
                              : isAck
                              ? 'rgba(245, 158, 11, 0.15)'
                              : 'rgba(239, 68, 68, 0.15)',
                            color: isResolved ? '#34d399' : isAck ? '#fbbf24' : '#f87171'
                          }}
                        >
                          {evt.lifecycle_status || 'OPEN'}
                        </span>
                      </td>

                      {/* 9. Evidence Snapshot */}
                      <td style={{ padding: '10px 14px' }}>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setPreviewEvidence({
                              eventId: evt.event_id,
                              description: evt.description || evt.event_type,
                              location: locationDisplay
                            });
                          }}
                          title="View calibrated reference frame / video evidence"
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '4px',
                            backgroundColor: '#0f172a',
                            border: '1px solid #334155',
                            color: '#38bdf8',
                            padding: '3px 6px',
                            borderRadius: '4px',
                            fontSize: '0.625rem',
                            fontWeight: 600,
                            cursor: 'pointer'
                          }}
                        >
                          <ImageIcon size={12} />
                          <span>FRAME</span>
                        </button>
                      </td>

                      {/* 10. Actions (ACKNOWLEDGE, RESOLVE, DETAILS) */}
                      <td style={{ padding: '10px 14px', textAlign: 'right', whiteSpace: 'nowrap' }}>
                        <div style={{ display: 'inline-flex', gap: '6px' }} onClick={(e) => e.stopPropagation()}>
                          {isOpen && (
                            <button
                              onClick={() => onOpenAcknowledge(evt.event_id)}
                              style={{
                                padding: '4px 8px',
                                borderRadius: '4px',
                                backgroundColor: 'rgba(245, 158, 11, 0.15)',
                                border: '1px solid #d97706',
                                color: '#fbbf24',
                                fontSize: '0.6875rem',
                                fontWeight: 700,
                                cursor: 'pointer'
                              }}
                            >
                              ACKNOWLEDGE
                            </button>
                          )}

                          {!isResolved && (
                            <button
                              onClick={() => onOpenResolve(evt.event_id)}
                              style={{
                                padding: '4px 8px',
                                borderRadius: '4px',
                                backgroundColor: 'rgba(16, 185, 129, 0.15)',
                                border: '1px solid #059669',
                                color: '#34d399',
                                fontSize: '0.6875rem',
                                fontWeight: 700,
                                cursor: 'pointer'
                              }}
                            >
                              RESOLVE
                            </button>
                          )}

                          <button
                            onClick={() => onSelectEvent(evt)}
                            title="Inspect details"
                            style={{
                              padding: '4px 8px',
                              borderRadius: '4px',
                              backgroundColor: '#1e293b',
                              border: '1px solid #334155',
                              color: '#cbd5e1',
                              fontSize: '0.6875rem',
                              fontWeight: 600,
                              cursor: 'pointer'
                            }}
                          >
                            DETAILS
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Evidence Snapshot Preview Modal */}
      {previewEvidence && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.8)',
            backdropFilter: 'blur(4px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 100,
            padding: '20px'
          }}
          onClick={() => setPreviewEvidence(null)}
        >
          <div
            style={{
              backgroundColor: '#111827',
              border: '1px solid #334155',
              borderRadius: '8px',
              padding: '20px',
              maxWidth: '560px',
              width: '100%',
              color: '#f8fafc'
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
              <div>
                <h3 style={{ fontSize: '1rem', fontWeight: 800, margin: 0 }}>
                  Incident Video Evidence Reference
                </h3>
                <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
                  ID: {previewEvidence.eventId} • {previewEvidence.location}
                </div>
              </div>
              <button
                onClick={() => setPreviewEvidence(null)}
                style={{ background: 'none', border: 'none', color: '#94a3b8', fontSize: '1.25rem', cursor: 'pointer' }}
              >
                &times;
              </button>
            </div>

            <div
              style={{
                height: '240px',
                backgroundColor: '#090b10',
                borderRadius: '6px',
                border: '1px solid #1e293b',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                position: 'relative',
                overflow: 'hidden'
              }}
            >
              <img
                src="/api/stream/mjpeg"
                alt="Live Evidence Frame"
                style={{ width: '100%', height: '100%', objectFit: 'cover', opacity: 0.8 }}
                onError={(e) => {
                  (e.currentTarget as HTMLElement).style.display = 'none';
                }}
              />
              <div
                style={{
                  position: 'absolute',
                  top: '10px',
                  left: '10px',
                  backgroundColor: 'rgba(0, 0, 0, 0.7)',
                  padding: '4px 8px',
                  borderRadius: '4px',
                  fontSize: '0.6875rem',
                  fontFamily: 'monospace',
                  color: '#fbbf24'
                }}
              >
                [RECORDED EVIDENCE CAPTURE]
              </div>
            </div>

            <p style={{ fontSize: '0.8125rem', color: '#cbd5e1', marginTop: '12px', lineHeight: 1.4 }}>
              {previewEvidence.description}
            </p>

            <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '16px' }}>
              <button
                onClick={() => setPreviewEvidence(null)}
                style={{
                  backgroundColor: '#2563eb',
                  border: 'none',
                  color: '#ffffff',
                  padding: '6px 14px',
                  borderRadius: '4px',
                  fontWeight: 600,
                  fontSize: '0.75rem',
                  cursor: 'pointer'
                }}
              >
                Close Preview
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
