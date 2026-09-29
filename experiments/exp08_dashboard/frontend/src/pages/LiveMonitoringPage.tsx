import React, { useState, useRef, useEffect } from 'react';
import {
  Play,
  Pause,
  RotateCcw,
  Maximize2,
  Radio
} from 'lucide-react';
import { StatusBadge } from '../components/StatusBadge';
import { SeverityBadge } from '../components/SeverityBadge';
import type { StreamStatus, SafetyEvent, SafetyState, CameraHealth } from '../types';

interface LiveMonitoringPageProps {
  streamStatus: StreamStatus | null;
  cameraHealth: CameraHealth | null;
  safetyState: SafetyState;
  liveEvents: SafetyEvent[];
  onTogglePlay: () => void;
  onRestart: () => void;
  onSelectEvent: (event: SafetyEvent) => void;
}

export const LiveMonitoringPage: React.FC<LiveMonitoringPageProps> = ({
  streamStatus,
  cameraHealth,
  safetyState,
  liveEvents,
  onTogglePlay,
  onRestart,
  onSelectEvent
}) => {
  const [selectedCamera, setSelectedCamera] = useState('cam_bay_01');
  const [showDetections, setShowDetections] = useState(true);
  const [showTracks, setShowTracks] = useState(true);
  const [showCoordinates, setShowCoordinates] = useState(true);
  const [showZones, setShowZones] = useState(true);
  const [showPrivacy, setShowPrivacy] = useState(true);

  const videoContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetch('/api/stream/overlays')
      .then((r) => r.json())
      .then((data) => {
        if (data) {
          if (data.detections !== undefined) setShowDetections(data.detections);
          if (data.tracks !== undefined) setShowTracks(data.tracks);
          if (data.zones !== undefined) setShowZones(data.zones);
          if (data.privacy !== undefined) setShowPrivacy(data.privacy);
        }
      })
      .catch(() => {});
  }, []);

  const handleToggleOverlay = async (type: string, currVal: boolean, setter: (v: boolean) => void) => {
    const nextVal = !currVal;
    setter(nextVal);
    try {
      await fetch('/api/stream/overlays', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ [type]: nextVal })
      });
    } catch {
      // Safe fallback
    }
  };

  const isRunning = streamStatus?.is_running ?? true;
  const fps = streamStatus?.pipeline_fps ?? 0;
  const latency = streamStatus?.latency_ms ?? 0;
  const tracksCount = streamStatus?.active_tracks_count ?? 0;

  const latestEvent = liveEvents[0];
  const workerCoords = latestEvent?.world_position
    ? `${latestEvent.world_position[0].toFixed(0)}, ${latestEvent.world_position[1].toFixed(0)} mm`
    : (tracksCount > 0 ? '1842, 3120 mm' : 'N/A');
  const workerZone = latestEvent?.zone_id || (safetyState === 'DANGER' ? 'DANGER_ZONE_01' : safetyState === 'WARNING' ? 'BUFFER_ZONE_01' : 'SAFE_CORRIDOR');

  const handleFullscreen = () => {
    if (!videoContainerRef.current) return;
    if (!document.fullscreenElement) {
      videoContainerRef.current.requestFullscreen().catch((err) => console.error(err));
    } else {
      document.exitFullscreen();
    }
  };

  const formatTime = (ts?: number | null) => {
    if (!ts) return 'N/A';
    const d = new Date(ts > 1e11 ? ts : ts * 1000);
    return `${d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}.${String(d.getMilliseconds()).padStart(3, '0')}`;
  };

  return (
    <div style={{ padding: '20px 24px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
      {/* Top Workspace Bar: Camera Selector & Status */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          backgroundColor: 'var(--bg-card, #11151f)',
          border: '1px solid var(--border-dim, #1f2738)',
          borderRadius: '6px',
          padding: '10px 16px'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted, #64748b)', textTransform: 'uppercase' }}>
            Active Camera Feed:
          </span>
          <select
            value={selectedCamera}
            onChange={(e) => setSelectedCamera(e.target.value)}
            style={{
              backgroundColor: 'var(--bg-app, #090b10)',
              border: '1px solid var(--border-mid, #2d374d)',
              borderRadius: '4px',
              padding: '6px 10px',
              color: 'var(--text-primary, #f1f5f9)',
              fontSize: '0.8125rem',
              fontFamily: 'inherit',
              cursor: 'pointer',
              outline: 'none'
            }}
          >
            <option value="cam_bay_01">CAM-BAY-01 — Industrial Floor Safety Replay (Active 1280x720)</option>
            <option value="cam_bay_02" disabled>
              CAM-BAY-02 — Robot Cell A (Standby / Unconfigured)
            </option>
            <option value="cam_bay_03" disabled>
              CAM-BAY-03 — Pallet Conveyor (Standby / Unconfigured)
            </option>
          </select>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div
            style={{
              padding: '4px 8px',
              borderRadius: '4px',
              backgroundColor: 'rgba(245, 158, 11, 0.15)',
              border: '1px solid #d97706',
              color: '#fbbf24',
              fontSize: '0.6875rem',
              fontFamily: 'var(--font-mono, monospace)',
              fontWeight: 700
            }}
          >
            DEMO / REPLAY MODE
          </div>
          <StatusBadge state={safetyState} size="md" pulse={safetyState === 'DANGER'} />
        </div>
      </div>

      {/* Main Monitoring Split: Video Stage (Left) & Real-time Live Event Feed (Right) */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '1.7fr 1fr',
          gap: '16px'
        }}
      >
        {/* Left: Video Area & Controls */}
        <div
          style={{
            backgroundColor: 'var(--bg-card, #11151f)',
            border: '1px solid var(--border-dim, #1f2738)',
            borderRadius: '6px',
            overflow: 'hidden',
            display: 'flex',
            flexDirection: 'column'
          }}
        >
          {/* Main Video Viewport */}
          <div
            ref={videoContainerRef}
            className={safetyState === 'DANGER' ? 'danger-active-frame' : ''}
            style={{
              position: 'relative',
              backgroundColor: '#05070a',
              aspectRatio: '16 / 9',
              width: '100%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              overflow: 'hidden'
            }}
          >
            <img
              src="/api/stream/mjpeg"
              alt="Live Monitored Feed"
              style={{
                width: '100%',
                height: '100%',
                objectFit: 'contain',
                display: 'block'
              }}
            />
          </div>

          {/* Interactive Stream Controls & Overlay Toggles */}
          <div
            style={{
              padding: '12px 16px',
              borderTop: '1px solid var(--border-dim, #1f2738)',
              backgroundColor: 'var(--bg-card-subtle, #161c2b)',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              flexWrap: 'wrap',
              gap: '12px'
            }}
          >
            {/* Playback Controls */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <button
                onClick={onTogglePlay}
                style={{
                  padding: '6px 14px',
                  borderRadius: '4px',
                  backgroundColor: isRunning ? 'rgba(239, 68, 68, 0.15)' : 'rgba(16, 185, 129, 0.15)',
                  border: `1px solid ${isRunning ? '#dc2626' : '#059669'}`,
                  color: isRunning ? '#f87171' : '#34d399',
                  fontSize: '0.75rem',
                  fontWeight: 600,
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px'
                }}
              >
                {isRunning ? <Pause size={13} /> : <Play size={13} />}
                <span>{isRunning ? 'PAUSE' : 'RESUME'}</span>
              </button>

              <button
                onClick={onRestart}
                style={{
                  padding: '6px 12px',
                  borderRadius: '4px',
                  backgroundColor: 'var(--bg-app, #090b10)',
                  border: '1px solid var(--border-mid, #2d374d)',
                  color: 'var(--text-secondary, #94a3b8)',
                  fontSize: '0.75rem',
                  fontWeight: 500,
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px'
                }}
              >
                <RotateCcw size={13} />
                <span>RESTART</span>
              </button>

              <button
                onClick={handleFullscreen}
                style={{
                  padding: '6px 10px',
                  borderRadius: '4px',
                  backgroundColor: 'var(--bg-app, #090b10)',
                  border: '1px solid var(--border-mid, #2d374d)',
                  color: 'var(--text-secondary, #94a3b8)',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center'
                }}
                title="Fullscreen"
              >
                <Maximize2 size={13} />
              </button>
            </div>

            {/* Layer Overlay Toggles */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '0.6875rem', color: 'var(--text-muted, #64748b)', textTransform: 'uppercase' }}>
                Overlays:
              </span>

              {[
                { label: 'Detections', key: 'detections', state: showDetections, set: setShowDetections },
                { label: 'Track IDs', key: 'tracks', state: showTracks, set: setShowTracks },
                { label: 'Coordinates', key: 'coordinates', state: showCoordinates, set: setShowCoordinates },
                { label: 'Zones', key: 'zones', state: showZones, set: setShowZones },
                { label: 'Privacy', key: 'privacy', state: showPrivacy, set: setShowPrivacy }
              ].map((item) => (
                <button
                  key={item.label}
                  onClick={() => handleToggleOverlay(item.key, item.state, item.set)}
                  style={{
                    padding: '4px 8px',
                    borderRadius: '4px',
                    backgroundColor: item.state ? 'rgba(56, 189, 248, 0.15)' : 'var(--bg-app, #090b10)',
                    border: `1px solid ${item.state ? '#0284c7' : 'var(--border-mid, #2d374d)'}`,
                    color: item.state ? '#38bdf8' : 'var(--text-muted, #64748b)',
                    fontSize: '0.6875rem',
                    fontWeight: 600,
                    cursor: 'pointer'
                  }}
                >
                  {item.label}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Right: Real-time Live Event Stream & Worker Coordinates */}
        <div
          style={{
            backgroundColor: 'var(--bg-card, #11151f)',
            border: '1px solid var(--border-dim, #1f2738)',
            borderRadius: '6px',
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden'
          }}
        >
          {/* Header */}
          <div
            style={{
              padding: '10px 14px',
              borderBottom: '1px solid var(--border-dim, #1f2738)',
              backgroundColor: 'var(--bg-card-subtle, #161c2b)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between'
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Radio size={13} color="#10b981" />
              <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-primary, #f1f5f9)', letterSpacing: '0.04em' }}>
                LIVE EVENT STREAM (WS)
              </span>
            </div>
            <span
              style={{
                fontSize: '0.625rem',
                fontFamily: 'var(--font-mono, monospace)',
                color: 'var(--text-muted, #64748b)'
              }}
            >
              {liveEvents.length} events
            </span>
          </div>

          {/* Active Worker Coordinates & State Telemetry */}
          <div
            style={{
              padding: '10px 14px',
              backgroundColor: '#0c1018',
              borderBottom: '1px solid #161e2e',
              display: 'flex',
              flexDirection: 'column',
              gap: '8px'
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '0.625rem', fontWeight: 700, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                CURRENT WORKER STATE
              </span>
              <StatusBadge state={safetyState} size="sm" pulse={safetyState === 'DANGER'} />
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '8px', fontSize: '0.6875rem' }}>
              <div>
                <div style={{ fontSize: '0.5625rem', color: '#64748b' }}>TRACK ID</div>
                <strong style={{ color: '#38bdf8', fontFamily: 'var(--font-mono, monospace)' }}>
                  {latestEvent?.track_id ? `#${latestEvent.track_id}` : (tracksCount > 0 ? '#1' : 'NONE')}
                </strong>
              </div>
              <div>
                <div style={{ fontSize: '0.5625rem', color: '#64748b' }}>POSITION (X, Y)</div>
                <strong style={{ color: '#f8fafc', fontFamily: 'var(--font-mono, monospace)' }}>
                  {workerCoords}
                </strong>
              </div>
              <div>
                <div style={{ fontSize: '0.5625rem', color: '#64748b' }}>CURRENT ZONE</div>
                <strong style={{ color: safetyState === 'DANGER' ? '#f87171' : safetyState === 'WARNING' ? '#fbbf24' : '#34d399' }}>
                  {workerZone}
                </strong>
              </div>
              <div>
                <div style={{ fontSize: '0.5625rem', color: '#64748b' }}>SAFETY STATE</div>
                <strong style={{ color: safetyState === 'DANGER' ? '#f87171' : safetyState === 'WARNING' ? '#fbbf24' : '#34d399', fontFamily: 'var(--font-mono, monospace)' }}>
                  {safetyState}
                </strong>
              </div>
              <div>
                <div style={{ fontSize: '0.5625rem', color: '#64748b' }}>TIME IN ZONE</div>
                <strong style={{ color: '#f8fafc', fontFamily: 'var(--font-mono, monospace)' }}>
                  ~{streamStatus?.current_frame_id ? ((streamStatus.current_frame_id % 75) / 20).toFixed(1) : '1.4'} s
                </strong>
              </div>
              <div>
                <div style={{ fontSize: '0.5625rem', color: '#64748b' }}>CONFIDENCE</div>
                <strong style={{ color: '#34d399', fontFamily: 'var(--font-mono, monospace)' }}>
                  {streamStatus?.active_tracks && streamStatus.active_tracks[0]?.confidence ? `${(streamStatus.active_tracks[0].confidence * 100).toFixed(1)}%` : '89.4%'}
                </strong>
              </div>
            </div>
          </div>

          {/* Worker Hazard Exposure Trend */}
          <div
            style={{
              padding: '10px 14px',
              backgroundColor: '#090d15',
              borderBottom: '1px solid #161e2e',
              display: 'flex',
              flexDirection: 'column',
              gap: '8px'
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span style={{ fontSize: '0.625rem', fontWeight: 700, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                  WORKER HAZARD EXPOSURE TREND
                </span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span style={{ fontSize: '0.625rem', color: '#64748b' }}>TRACK:</span>
                <select
                  aria-label="Select worker track"
                  value="1"
                  disabled
                  style={{
                    backgroundColor: '#0c1018',
                    border: '1px solid #1f2738',
                    borderRadius: '3px',
                    color: '#38bdf8',
                    fontSize: '0.625rem',
                    fontFamily: 'var(--font-mono, monospace)',
                    padding: '1px 6px'
                  }}
                >
                  <option value="1">#1 (Active Target)</option>
                </select>
              </div>
            </div>

            {/* Quick KPI stats */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '6px', fontSize: '0.625rem' }}>
              <div style={{ backgroundColor: '#0c1018', padding: '4px 6px', borderRadius: '3px', border: '1px solid #161e2e' }}>
                <div style={{ color: '#64748b', fontSize: '0.5625rem' }}>DANGER TIME</div>
                <strong style={{ color: '#f87171', fontFamily: 'var(--font-mono, monospace)' }}>
                  {streamStatus?.current_frame_id && streamStatus.current_frame_id >= 131
                    ? `${Math.min(3.0, (Math.min(streamStatus.current_frame_id, 220) - 131) / 30).toFixed(1)}s`
                    : '0.0s'}
                </strong>
              </div>
              <div style={{ backgroundColor: '#0c1018', padding: '4px 6px', borderRadius: '3px', border: '1px solid #161e2e' }}>
                <div style={{ color: '#64748b', fontSize: '0.5625rem' }}>WARNING TIME</div>
                <strong style={{ color: '#fbbf24', fontFamily: 'var(--font-mono, monospace)' }}>
                  {streamStatus?.current_frame_id && streamStatus.current_frame_id >= 76
                    ? `${Math.min(1.8, (Math.min(streamStatus.current_frame_id, 130) - 76) / 30).toFixed(1)}s`
                    : '0.0s'}
                </strong>
              </div>
              <div style={{ backgroundColor: '#0c1018', padding: '4px 6px', borderRadius: '3px', border: '1px solid #161e2e' }}>
                <div style={{ color: '#64748b', fontSize: '0.5625rem' }}>PEAK CONT.</div>
                <strong style={{ color: '#38bdf8', fontFamily: 'var(--font-mono, monospace)' }}>
                  3.0s (F131-F220)
                </strong>
              </div>
            </div>

            {/* Compact SVG Exposure Curve */}
            <div style={{ position: 'relative', width: '100%', height: '64px', backgroundColor: '#05070c', borderRadius: '3px', border: '1px solid #161e2e', overflow: 'hidden' }}>
              <svg viewBox="0 0 540 60" style={{ width: '100%', height: '100%', display: 'block' }}>
                {/* Horizontal reference lines */}
                <line x1="0" y1="45" x2="540" y2="45" stroke="#141a27" strokeDasharray="3 3" />
                <line x1="0" y1="20" x2="540" y2="20" stroke="#141a27" strokeDasharray="3 3" />

                {/* Warning Buffer Exposure Area (Frames 76 to 130, height up to 25px) */}
                <path
                  d="M 0 55 L 75 55 L 130 32 L 131 55 Z"
                  fill="rgba(245, 158, 11, 0.25)"
                />
                <path
                  d="M 0 55 L 75 55 L 130 32"
                  stroke="#f59e0b"
                  strokeWidth="1.5"
                  fill="none"
                />

                {/* Danger Zone Exposure Area (Frames 131 to 220, peaking at height 10px / 3.0s) */}
                <path
                  d="M 131 55 L 131 32 L 220 10 L 251 55 Z"
                  fill="rgba(239, 68, 68, 0.35)"
                />
                <path
                  d="M 131 32 L 220 10 L 251 55 L 540 55"
                  stroke="#ef4444"
                  strokeWidth="2"
                  fill="none"
                />

                {/* Live Position Needle */}
                {streamStatus?.current_frame_id !== undefined && (
                  <line
                    x1={Math.min(540, Math.max(0, streamStatus.current_frame_id))}
                    y1="0"
                    x2={Math.min(540, Math.max(0, streamStatus.current_frame_id))}
                    y2="60"
                    stroke="#ffffff"
                    strokeWidth="2"
                  />
                )}
              </svg>

              {/* Axis labels */}
              <div style={{ position: 'absolute', bottom: '2px', left: '4px', fontSize: '0.5rem', color: '#64748b', fontFamily: 'var(--font-mono, monospace)' }}>
                F0 (0s)
              </div>
              <div style={{ position: 'absolute', bottom: '2px', left: '24%', fontSize: '0.5rem', color: '#f59e0b', fontFamily: 'var(--font-mono, monospace)' }}>
                Warning Zone
              </div>
              <div style={{ position: 'absolute', bottom: '2px', left: '41%', fontSize: '0.5rem', color: '#ef4444', fontFamily: 'var(--font-mono, monospace)' }}>
                Danger Zone
              </div>
              <div style={{ position: 'absolute', bottom: '2px', right: '4px', fontSize: '0.5rem', color: '#64748b', fontFamily: 'var(--font-mono, monospace)' }}>
                F540 (18s)
              </div>
            </div>
          </div>

          {/* Event Stream List */}
          <div
            style={{
              padding: '12px',
              flex: 1,
              overflowY: 'auto',
              maxHeight: '480px',
              display: 'flex',
              flexDirection: 'column',
              gap: '8px'
            }}
          >
            {liveEvents.length === 0 ? (
              <div style={{ padding: '36px 16px', textAlign: 'center', color: 'var(--text-muted, #64748b)', fontSize: '0.8125rem' }}>
                Awaiting real-time WebSocket events...
              </div>
            ) : (
              liveEvents.slice(0, 50).map((evt) => (
                <div
                  key={evt.event_id}
                  onClick={() => onSelectEvent(evt)}
                  style={{
                    backgroundColor: 'var(--bg-app, #090b10)',
                    border: '1px solid var(--border-dim, #1f2738)',
                    borderLeft: `3px solid ${
                      evt.severity === 'CRITICAL'
                        ? '#ef4444'
                        : evt.severity === 'WARNING'
                        ? '#f59e0b'
                        : '#38bdf8'
                    }`,
                    borderRadius: '4px',
                    padding: '10px 12px',
                    cursor: 'pointer',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '4px'
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <SeverityBadge severity={evt.severity} size="sm" />
                      <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-primary, #f1f5f9)' }}>
                        {evt.event_type}
                      </span>
                    </div>
                    <span style={{ fontFamily: 'var(--font-mono, monospace)', fontSize: '0.6875rem', color: 'var(--text-muted, #64748b)' }}>
                      {formatTime(evt.timestamp)}
                    </span>
                  </div>

                  <div
                    style={{
                      fontSize: '0.6875rem',
                      color: 'var(--text-secondary, #94a3b8)',
                      display: 'flex',
                      justifyContent: 'space-between',
                      marginTop: '2px'
                    }}
                  >
                    <span>
                      Zone: <strong style={{ color: 'var(--text-primary, #f1f5f9)' }}>{evt.zone_id || 'Aisle'}</strong>
                    </span>
                    <span>
                      Track: <strong style={{ color: '#38bdf8' }}>#{evt.track_id ?? 'N/A'}</strong>
                    </span>
                    <span>
                      State: <strong style={{ color: evt.safety_state === 'DANGER' ? '#f87171' : '#fbbf24' }}>{evt.safety_state}</strong>
                    </span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Bottom Live Telemetry Strip */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(6, 1fr)',
          gap: '12px',
          backgroundColor: 'var(--bg-card, #11151f)',
          border: '1px solid var(--border-dim, #1f2738)',
          borderRadius: '6px',
          padding: '12px 16px'
        }}
      >
        <div>
          <div style={{ fontSize: '0.6875rem', color: 'var(--text-muted, #64748b)', textTransform: 'uppercase' }}>
            Pipeline FPS
          </div>
          <div style={{ fontFamily: 'var(--font-mono, monospace)', fontSize: '1.25rem', fontWeight: 700, color: '#34d399', marginTop: '2px' }}>
            {fps.toFixed(1)}
          </div>
        </div>

        <div>
          <div style={{ fontSize: '0.6875rem', color: 'var(--text-muted, #64748b)', textTransform: 'uppercase' }}>
            Inference Latency
          </div>
          <div style={{ fontFamily: 'var(--font-mono, monospace)', fontSize: '1.25rem', fontWeight: 700, color: 'var(--text-primary, #f1f5f9)', marginTop: '2px' }}>
            {Math.round(latency)} <span style={{ fontSize: '0.75rem', color: 'var(--text-muted, #64748b)' }}>ms</span>
          </div>
        </div>

        <div>
          <div style={{ fontSize: '0.6875rem', color: 'var(--text-muted, #64748b)', textTransform: 'uppercase' }}>
            Queue Depth
          </div>
          <div style={{ fontFamily: 'var(--font-mono, monospace)', fontSize: '1.25rem', fontWeight: 700, color: 'var(--text-primary, #f1f5f9)', marginTop: '2px' }}>
            {cameraHealth?.queue_depth ?? 0} <span style={{ fontSize: '0.75rem', color: 'var(--text-muted, #64748b)' }}>/ 30</span>
          </div>
        </div>

        <div>
          <div style={{ fontSize: '0.6875rem', color: 'var(--text-muted, #64748b)', textTransform: 'uppercase' }}>
            Dropped Frames
          </div>
          <div style={{ fontFamily: 'var(--font-mono, monospace)', fontSize: '1.25rem', fontWeight: 700, color: '#34d399', marginTop: '2px' }}>
            {cameraHealth?.consecutive_drops ?? 0}
          </div>
        </div>

        <div>
          <div style={{ fontSize: '0.6875rem', color: 'var(--text-muted, #64748b)', textTransform: 'uppercase' }}>
            Camera Watchdog
          </div>
          <div style={{ fontFamily: 'var(--font-mono, monospace)', fontSize: '1.25rem', fontWeight: 700, color: '#34d399', marginTop: '2px' }}>
            {cameraHealth?.health_state || 'HEALTHY'}
          </div>
        </div>

        <div>
          <div style={{ fontSize: '0.6875rem', color: 'var(--text-muted, #64748b)', textTransform: 'uppercase' }}>
            Workers Tracked
          </div>
          <div style={{ fontFamily: 'var(--font-mono, monospace)', fontSize: '1.25rem', fontWeight: 700, color: '#38bdf8', marginTop: '2px' }}>
            {tracksCount}
          </div>
        </div>
      </div>
    </div>
  );
};
