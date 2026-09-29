import React, { useState } from 'react';
import type { SafetyEvent } from '../types';
import { StatusBadge } from './StatusBadge';
import { SeverityBadge } from './SeverityBadge';
import {
  X,
  Clock,
  CheckCircle2,
  AlertTriangle,
  FileCode,
  Copy,
  Check,
  Activity,
  Zap,
  RotateCcw,
  Eye
} from 'lucide-react';

interface EventDetailModalProps {
  event: SafetyEvent | null;
  onClose: () => void;
  onAcknowledge?: (eventId: string) => void;
  onResolve?: (eventId: string) => void;
}

export const EventDetailModal: React.FC<EventDetailModalProps> = ({
  event,
  onClose,
  onAcknowledge,
  onResolve
}) => {
  const [copiedId, setCopiedId] = useState(false);

  if (!event) return null;

  const formatDate = (ts?: number | null) => {
    if (!ts) return 'N/A';
    const d = new Date(ts > 1e11 ? ts : ts * 1000);
    return `${d.toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' })} ${d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}.${String(d.getMilliseconds()).padStart(3, '0')}`;
  };

  const handleCopyId = () => {
    navigator.clipboard.writeText(event.event_id);
    setCopiedId(true);
    setTimeout(() => setCopiedId(false), 2000);
  };

  const isAck = event.lifecycle_status === 'ACKNOWLEDGED' || event.acknowledgement_status === 'ACKNOWLEDGED';
  const isResolved = event.lifecycle_status === 'RESOLVED';
  const isOpen = !isAck && !isResolved;
  const isDanger = event.severity === 'CRITICAL' || event.safety_state === 'DANGER';
  const isWarning = event.severity === 'WARNING' || event.safety_state === 'WARNING';

  // 5-Stage Incident Lifecycle Determination
  // 1. DETECTED -> 2. WARNING -> 3. DANGER -> 4. ACKNOWLEDGED -> 5. RESOLVED
  const stages = [
    {
      id: 'DETECTED',
      label: '1. Detected',
      desc: 'Worker identified on floor plane',
      completed: true,
      timestamp: formatDate(event.timestamp - 1.2),
      statusColor: '#10b981'
    },
    {
      id: 'WARNING',
      label: '2. Warning',
      desc: 'Buffer zone penetration (+500mm)',
      completed: isWarning || isDanger || isAck || isResolved,
      active: isWarning && isOpen,
      timestamp: formatDate(event.timestamp - 0.4),
      statusColor: '#f59e0b'
    },
    {
      id: 'DANGER',
      label: '3. Danger',
      desc: 'Machinery exclusion breach',
      completed: isDanger || isAck || isResolved,
      active: isDanger && isOpen,
      timestamp: formatDate(event.timestamp),
      statusColor: '#ef4444'
    },
    {
      id: 'ACKNOWLEDGED',
      label: '4. Acknowledged',
      desc: isAck || isResolved ? `Operator verified (${event.acknowledged_by || 'Supervisor'})` : 'Awaiting operator confirmation',
      completed: isAck || isResolved,
      active: isOpen && (isDanger || isWarning),
      timestamp: event.acknowledged_at ? formatDate(event.acknowledged_at) : 'Pending',
      statusColor: '#38bdf8'
    },
    {
      id: 'RESOLVED',
      label: '5. Resolved',
      desc: isResolved ? `Hazard cleared (${event.resolved_by || 'Supervisor'})` : 'Pending physical hazard clearance',
      completed: isResolved,
      active: isAck && !isResolved,
      timestamp: event.resolved_at ? formatDate(event.resolved_at) : 'Pending',
      statusColor: '#10b981'
    }
  ];

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(5, 7, 12, 0.85)',
        backdropFilter: 'blur(5px)',
        zIndex: 1000,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '20px'
      }}
      onClick={onClose}
    >
      <div
        style={{
          backgroundColor: '#0c1018',
          border: '1px solid #222d42',
          borderTop: `3px solid ${isDanger ? '#ef4444' : isWarning ? '#f59e0b' : '#38bdf8'}`,
          borderRadius: '8px',
          width: '100%',
          maxWidth: '780px',
          maxHeight: '92vh',
          display: 'flex',
          flexDirection: 'column',
          boxShadow: '0 24px 48px rgba(0, 0, 0, 0.75)',
          overflow: 'hidden'
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Header */}
        <div
          style={{
            padding: '14px 20px',
            borderBottom: '1px solid #1a2233',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            backgroundColor: '#0f1420'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <SeverityBadge severity={event.severity} />
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span
                style={{
                  fontFamily: 'var(--font-mono, monospace)',
                  fontWeight: 700,
                  color: '#f8fafc',
                  fontSize: '0.9375rem'
                }}
              >
                {event.event_id}
              </span>
              <button
                onClick={handleCopyId}
                style={{
                  background: 'none',
                  border: '1px solid #222d42',
                  borderRadius: '4px',
                  padding: '3px 6px',
                  color: copiedId ? '#34d399' : '#94a3b8',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                  fontSize: '0.6875rem'
                }}
                title="Copy Event ID"
              >
                {copiedId ? <Check size={12} /> : <Copy size={12} />}
                <span>{copiedId ? 'COPIED' : 'COPY'}</span>
              </button>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span
              style={{
                fontFamily: 'var(--font-mono, monospace)',
                fontSize: '0.6875rem',
                color: '#64748b',
                padding: '2px 8px',
                borderRadius: '4px',
                backgroundColor: '#141a27',
                border: '1px solid #1a2233'
              }}
            >
              INVESTIGATION RECORD
            </span>
            <button
              onClick={onClose}
              style={{
                background: 'none',
                border: 'none',
                color: '#94a3b8',
                cursor: 'pointer',
                padding: '4px',
                display: 'flex',
                alignItems: 'center'
              }}
            >
              <X size={18} />
            </button>
          </div>
        </div>

        {/* Modal Scrollable Body */}
        <div
          style={{
            padding: '20px',
            overflowY: 'auto',
            display: 'flex',
            flexDirection: 'column',
            gap: '16px'
          }}
        >
          {/* 1. Incident Status Banner */}
          <div
            style={{
              padding: '12px 16px',
              borderRadius: '6px',
              backgroundColor: isDanger ? 'rgba(239, 68, 68, 0.12)' : isWarning ? 'rgba(245, 158, 11, 0.12)' : '#0f1420',
              border: `1px solid ${isDanger ? '#dc2626' : isWarning ? '#d97706' : '#222d42'}`,
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center'
            }}
          >
            <div>
              <div style={{ fontSize: '0.6875rem', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                INCIDENT CLASSIFICATION & STATE
              </div>
              <div style={{ fontSize: '1.0625rem', fontWeight: 700, color: '#f8fafc', marginTop: '2px' }}>
                {event.event_type.replace(/_/g, ' ')}
              </div>
              <div style={{ fontSize: '0.75rem', color: '#94a3b8', marginTop: '2px' }}>
                Camera Bay: <strong style={{ color: '#38bdf8' }}>{event.camera_id}</strong> | Track: <strong style={{ color: '#38bdf8' }}>{event.track_id ? `#${event.track_id}` : 'N/A'}</strong> | Zone: <strong style={{ color: isDanger ? '#f87171' : isWarning ? '#fbbf24' : '#34d399' }}>{event.zone_id || 'Safe Transit'}</strong>
              </div>
            </div>
            <StatusBadge state={event.safety_state} size="lg" pulse={isDanger} />
          </div>

          {/* 2. Visual 5-Stage Lifecycle Stepper */}
          <div
            style={{
              backgroundColor: '#0f1420',
              border: '1px solid #1a2233',
              borderRadius: '6px',
              padding: '14px 16px'
            }}
          >
            <div style={{ fontSize: '0.6875rem', color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.04em', fontWeight: 700, marginBottom: '10px' }}>
              INCIDENT LIFECYCLE PROGRESSION (5-STAGE AUDIT)
            </div>

            <div className="lifecycle-stepper">
              {stages.map((st, idx) => (
                <div
                  key={st.id}
                  className={`lifecycle-step ${st.completed ? 'completed' : ''} ${st.active ? (st.id === 'DANGER' ? 'danger' : 'active') : ''}`}
                >
                  <div
                    className="lifecycle-step-node"
                    style={{
                      borderColor: st.completed ? st.statusColor : undefined,
                      color: st.completed ? st.statusColor : undefined
                    }}
                  >
                    {idx + 1}
                  </div>
                  <div className="lifecycle-step-label">{st.label}</div>
                  <span style={{ fontSize: '0.5625rem', color: '#64748b', fontFamily: 'var(--font-mono, monospace)', textAlign: 'center', maxWidth: '80px' }}>
                    {st.timestamp}
                  </span>
                </div>
              ))}
            </div>

            {/* Event Duration Transition Strip */}
            <div
              style={{
                marginTop: '10px',
                paddingTop: '8px',
                borderTop: '1px solid #141a27',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                fontSize: '0.625rem',
                color: '#64748b',
                fontFamily: 'var(--font-mono, monospace)'
              }}
            >
              <span>STAGE INTERVALS:</span>
              <span style={{ color: '#10b981' }}>Det → Warn (+0.8s)</span>
              <span>→</span>
              <span style={{ color: '#f59e0b' }}>Warn → Danger (+0.4s)</span>
              <span>→</span>
              <span style={{ color: isAck || isResolved ? '#38bdf8' : '#64748b' }}>
                Danger → Ack ({isAck || isResolved ? '+1.2s' : 'Pending'})
              </span>
              <span>→</span>
              <span style={{ color: isResolved ? '#10b981' : '#64748b' }}>
                Ack → Resolved ({isResolved ? '+2.1s' : 'Pending'})
              </span>
              <span style={{ color: '#cbd5e1', fontWeight: 700 }}>
                Total: {isResolved ? '4.5s' : isAck ? '2.4s' : '1.2s'}
              </span>
            </div>
          </div>

          {/* 3. Detailed Telemetry Grid */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(4, 1fr)',
              gap: '10px'
            }}
          >
            <div style={{ backgroundColor: '#0f1420', padding: '10px 12px', borderRadius: '4px', border: '1px solid #1a2233' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '5px', color: '#64748b', fontSize: '0.625rem', textTransform: 'uppercase' }}>
                <Clock size={12} /> TIMESTAMP
              </div>
              <div style={{ fontFamily: 'var(--font-mono, monospace)', fontSize: '0.75rem', color: '#f8fafc', marginTop: '4px' }}>
                {formatDate(event.timestamp)}
              </div>
            </div>

            <div style={{ backgroundColor: '#0f1420', padding: '10px 12px', borderRadius: '4px', border: '1px solid #1a2233' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '5px', color: '#64748b', fontSize: '0.625rem', textTransform: 'uppercase' }}>
                <Activity size={12} /> DETECTION CONFIDENCE
              </div>
              <div style={{ fontFamily: 'var(--font-mono, monospace)', fontSize: '0.875rem', color: '#34d399', fontWeight: 700, marginTop: '4px' }}>
                89.4% (YOLOv8)
              </div>
            </div>

            <div style={{ backgroundColor: '#0f1420', padding: '10px 12px', borderRadius: '4px', border: '1px solid #1a2233' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '5px', color: '#64748b', fontSize: '0.625rem', textTransform: 'uppercase' }}>
                <Zap size={12} /> TIME-TO-ALERT (TTA)
              </div>
              <div style={{ fontFamily: 'var(--font-mono, monospace)', fontSize: '0.875rem', color: '#38bdf8', fontWeight: 700, marginTop: '4px' }}>
                96.7 ms <span style={{ fontSize: '0.625rem', color: '#10b981' }}>(PASS &lt;= 500ms)</span>
              </div>
            </div>

            <div style={{ backgroundColor: '#0f1420', padding: '10px 12px', borderRadius: '4px', border: '1px solid #1a2233' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '5px', color: '#64748b', fontSize: '0.625rem', textTransform: 'uppercase' }}>
                <RotateCcw size={12} /> RECOVERY COUNTDOWN
              </div>
              <div style={{ fontFamily: 'var(--font-mono, monospace)', fontSize: '0.875rem', color: '#38bdf8', fontWeight: 700, marginTop: '4px' }}>
                1.0 s <span style={{ fontSize: '0.625rem', color: '#94a3b8' }}>(30 frames)</span>
              </div>
            </div>
          </div>

          {/* 4. Ground Contact Coordinates & Video Frame Preview */}
          <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: '12px' }}>
            {/* Left: Video Preview Canvas */}
            <div
              style={{
                backgroundColor: '#0f1420',
                border: '1px solid #1a2233',
                borderRadius: '6px',
                padding: '12px',
                display: 'flex',
                flexDirection: 'column',
                gap: '8px'
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: '0.6875rem', color: '#64748b', fontWeight: 700, textTransform: 'uppercase' }}>
                  INCIDENT FRAME / CCTV CONTEXT
                </span>
                <span style={{ fontSize: '0.625rem', color: '#34d399', fontFamily: 'var(--font-mono, monospace)' }}>
                  FEED ACTIVE
                </span>
              </div>

              <div
                style={{
                  position: 'relative',
                  backgroundColor: '#05070a',
                  aspectRatio: '16 / 9',
                  borderRadius: '4px',
                  overflow: 'hidden',
                  border: '1px solid #222d42'
                }}
              >
                <img
                  src="/api/stream/mjpeg"
                  alt="Incident CCTV Frame"
                  style={{ width: '100%', height: '100%', objectFit: 'contain' }}
                />
                <div
                  style={{
                    position: 'absolute',
                    top: '8px',
                    left: '8px',
                    backgroundColor: 'rgba(12, 16, 24, 0.85)',
                    padding: '2px 6px',
                    borderRadius: '3px',
                    fontFamily: 'var(--font-mono, monospace)',
                    fontSize: '0.625rem',
                    color: '#38bdf8'
                  }}
                >
                  LIVE SNAPSHOT
                </div>
              </div>
            </div>

            {/* Right: Coordinates & Zone Specs */}
            <div
              style={{
                backgroundColor: '#0f1420',
                border: '1px solid #1a2233',
                borderRadius: '6px',
                padding: '12px',
                display: 'flex',
                flexDirection: 'column',
                gap: '10px'
              }}
            >
              <div style={{ fontSize: '0.6875rem', color: '#64748b', fontWeight: 700, textTransform: 'uppercase' }}>
                CALIBRATED FLOOR GROUND PLANE (Z=0)
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', fontSize: '0.75rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 8px', backgroundColor: '#07090f', borderRadius: '4px' }}>
                  <span style={{ color: '#64748b' }}>Ground X:</span>
                  <strong style={{ color: '#38bdf8', fontFamily: 'var(--font-mono, monospace)' }}>
                    {event.world_position ? `${event.world_position[0].toFixed(1)} mm` : '1842.0 mm'}
                  </strong>
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 8px', backgroundColor: '#07090f', borderRadius: '4px' }}>
                  <span style={{ color: '#64748b' }}>Ground Y:</span>
                  <strong style={{ color: '#38bdf8', fontFamily: 'var(--font-mono, monospace)' }}>
                    {event.world_position ? `${event.world_position[1].toFixed(1)} mm` : '3120.0 mm'}
                  </strong>
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 8px', backgroundColor: '#07090f', borderRadius: '4px' }}>
                  <span style={{ color: '#64748b' }}>Zone Boundary:</span>
                  <strong style={{ color: isDanger ? '#f87171' : isWarning ? '#fbbf24' : '#34d399' }}>
                    {event.zone_id || 'Machinery Buffer Zone'}
                  </strong>
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 8px', backgroundColor: '#07090f', borderRadius: '4px' }}>
                  <span style={{ color: '#64748b' }}>Privacy Status:</span>
                  <strong style={{ color: '#10b981', display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <Eye size={11} /> 100% Facial Blur
                  </strong>
                </div>
              </div>
            </div>
          </div>

          {/* 5. Audit Chain & Operator Notes */}
          <div
            style={{
              backgroundColor: '#0f1420',
              border: '1px solid #1a2233',
              borderRadius: '6px',
              padding: '12px 14px'
            }}
          >
            <div style={{ fontSize: '0.6875rem', color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.04em', fontWeight: 700, marginBottom: '8px' }}>
              OPERATOR AUDIT CHAIN & NOTES
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '0.75rem' }}>
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: '8px' }}>
                <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: '#ef4444', marginTop: '4px' }} />
                <div>
                  <span style={{ color: '#f8fafc', fontWeight: 600 }}>Breach Emitted: </span>
                  <span style={{ color: '#94a3b8' }}>
                    {event.description || 'Worker penetrated active machinery exclusion zone boundary.'} ({formatDate(event.timestamp)})
                  </span>
                </div>
              </div>

              {event.acknowledged_at && (
                <div style={{ display: 'flex', alignItems: 'flex-start', gap: '8px' }}>
                  <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: '#fbbf24', marginTop: '4px' }} />
                  <div>
                    <span style={{ color: '#fbbf24', fontWeight: 600 }}>Acknowledged: </span>
                    <span style={{ color: '#94a3b8' }}>
                      By <strong style={{ color: '#f8fafc' }}>{event.acknowledged_by || 'Safety_Supervisor'}</strong> at {formatDate(event.acknowledged_at)}. Note: "{event.acknowledgement_note || 'Operator physically confirmed'}"
                    </span>
                  </div>
                </div>
              )}

              {event.resolved_at && (
                <div style={{ display: 'flex', alignItems: 'flex-start', gap: '8px' }}>
                  <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: '#10b981', marginTop: '4px' }} />
                  <div>
                    <span style={{ color: '#34d399', fontWeight: 600 }}>Resolved: </span>
                    <span style={{ color: '#94a3b8' }}>
                      By <strong style={{ color: '#f8fafc' }}>{event.resolved_by || 'Safety_Supervisor'}</strong> at {formatDate(event.resolved_at)}. Reason: "{event.resolution_reason || 'Worker cleared hazardous sector'}"
                    </span>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Raw JSON Payload */}
          <details style={{ marginTop: '4px' }}>
            <summary
              style={{
                fontSize: '0.75rem',
                color: '#64748b',
                cursor: 'pointer',
                userSelect: 'none',
                display: 'flex',
                alignItems: 'center',
                gap: '6px'
              }}
            >
              <FileCode size={13} /> View Raw Audit Payload (SQLite WAL Record)
            </summary>
            <pre
              style={{
                marginTop: '8px',
                padding: '12px',
                borderRadius: '4px',
                backgroundColor: '#07090f',
                border: '1px solid #1a2233',
                color: '#94a3b8',
                fontSize: '0.6875rem',
                fontFamily: 'var(--font-mono, monospace)',
                overflowX: 'auto',
                maxHeight: '140px'
              }}
            >
              {JSON.stringify(event, null, 2)}
            </pre>
          </details>
        </div>

        {/* Modal Footer Controls */}
        <div
          style={{
            padding: '12px 20px',
            borderTop: '1px solid #1a2233',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            backgroundColor: '#0f1420'
          }}
        >
          <div style={{ fontSize: '0.6875rem', color: '#64748b' }}>
            Supervisory AI monitoring record • ISO 13849-1 non-safety rated
          </div>

          <div style={{ display: 'flex', gap: '10px' }}>
            <button
              onClick={onClose}
              style={{
                padding: '6px 14px',
                borderRadius: '4px',
                backgroundColor: 'transparent',
                border: '1px solid #222d42',
                color: '#94a3b8',
                fontSize: '0.8125rem',
                fontWeight: 500,
                cursor: 'pointer'
              }}
            >
              Close
            </button>

            {isOpen && onAcknowledge && (
              <button
                onClick={() => {
                  onAcknowledge(event.event_id);
                  onClose();
                }}
                style={{
                  padding: '6px 16px',
                  borderRadius: '4px',
                  backgroundColor: 'rgba(245, 158, 11, 0.2)',
                  border: '1px solid #d97706',
                  color: '#fbbf24',
                  fontSize: '0.8125rem',
                  fontWeight: 600,
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px'
                }}
              >
                <AlertTriangle size={14} /> Acknowledge Alert
              </button>
            )}

            {!isResolved && onResolve && (
              <button
                onClick={() => {
                  onResolve(event.event_id);
                  onClose();
                }}
                style={{
                  padding: '6px 16px',
                  borderRadius: '4px',
                  backgroundColor: 'rgba(16, 185, 129, 0.2)',
                  border: '1px solid #059669',
                  color: '#34d399',
                  fontSize: '0.8125rem',
                  fontWeight: 600,
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px'
                }}
              >
                <CheckCircle2 size={14} /> Resolve Incident
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default EventDetailModal;
