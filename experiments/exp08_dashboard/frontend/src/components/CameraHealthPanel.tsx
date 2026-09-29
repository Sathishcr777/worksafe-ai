import React from 'react';
import { Video } from 'lucide-react';
import type { CameraHealth } from '../types';

interface CameraHealthPanelProps {
  health: CameraHealth | null;
}

export const CameraHealthPanel: React.FC<CameraHealthPanelProps> = ({ health }) => {
  const state = health?.health_state ?? 'HEALTHY';
  const fps = health?.effective_fps ?? 0.0;
  const frozen = health?.frozen_frame_count ?? 0;
  const drops = health?.consecutive_drops ?? 0;
  const queueDepth = health?.queue_depth ?? 0;
  const maxQueue = health?.max_queue_depth ?? 5;
  const latency = health?.processing_latency_ms ?? 0.0;
  const failures = health?.failure_reasons ?? [];

  const isHealthy = state === 'HEALTHY';
  const isUnknown = state === 'UNKNOWN';

  return (
    <div className="card-panel">
      <div className="card-header">
        <h2>
          <Video size={16} />
          <span>Camera Health Watchdog ({health?.camera_id || 'cam_bay_01'})</span>
        </h2>
        <span
          className="mono"
          style={{
            fontSize: '0.75rem',
            padding: '2px 8px',
            borderRadius: '4px',
            fontWeight: 700,
            background: isHealthy
              ? 'rgba(16, 185, 129, 0.15)'
              : isUnknown
              ? 'rgba(168, 85, 247, 0.25)'
              : 'rgba(245, 158, 11, 0.2)',
            color: isHealthy ? '#34d399' : isUnknown ? '#c084fc' : '#fbbf24',
            border: `1px solid ${isHealthy ? '#059669' : isUnknown ? '#9333ea' : '#d97706'}`
          }}
        >
          {state}
        </span>
      </div>

      <div className="health-metrics-grid">
        <div className="metric-box">
          <div className="metric-label">Effective Camera FPS</div>
          <div className="metric-value">{fps.toFixed(1)}</div>
        </div>

        <div className="metric-box">
          <div className="metric-label">Processing Latency</div>
          <div className="metric-value">{latency.toFixed(1)} ms</div>
        </div>

        <div className="metric-box">
          <div className="metric-label">Frozen Frames (53μs check)</div>
          <div className="metric-value" style={{ color: frozen > 0 ? '#ef4444' : 'inherit' }}>
            {frozen}
          </div>
        </div>

        <div className="metric-box">
          <div className="metric-label">Queue Depth (DROP_OLDEST)</div>
          <div className="metric-value">
            {queueDepth} / {maxQueue}{' '}
            <span style={{ fontSize: '0.75rem', color: drops > 0 ? '#ef4444' : 'var(--text-muted)' }}>
              ({drops} drops)
            </span>
          </div>
        </div>
      </div>

      {failures.length > 0 && (
        <div style={{ padding: '0 16px 12px 16px' }}>
          <div style={{ fontSize: '0.75rem', color: '#f87171', fontWeight: 600, marginBottom: '4px' }}>
            Watchdog Failure Flags:
          </div>
          <ul style={{ paddingLeft: '18px', fontSize: '0.6875rem', color: '#fca5a5' }}>
            {failures.map((f, i) => (
              <li key={i}>{f}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};
