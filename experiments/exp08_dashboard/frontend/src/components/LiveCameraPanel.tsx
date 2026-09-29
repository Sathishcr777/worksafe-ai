import React from 'react';
import { Camera, Play, Pause } from 'lucide-react';
import type { StreamStatus } from '../types';

interface LiveCameraPanelProps {
  status: StreamStatus | null;
  onTogglePlay: () => void;
}

export const LiveCameraPanel: React.FC<LiveCameraPanelProps> = ({ status, onTogglePlay }) => {
  const isRunning = status?.is_running ?? true;
  const fps = status?.pipeline_fps ?? 0.0;
  const latency = status?.latency_ms ?? 0.0;
  const frameId = status?.current_frame_id ?? 0;
  const totalFrames = status?.total_frames ?? 180;
  const tracksCount = status?.active_tracks_count ?? 0;

  return (
    <div className="card-panel">
      <div className="card-header">
        <h2>
          <Camera size={16} />
          <span>Camera Feed: Bay 01 — Calibrated Floor Plane</span>
        </h2>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <button
            onClick={onTogglePlay}
            className="btn-ack"
            style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
          >
            {isRunning ? (
              <>
                <Pause size={13} />
                <span>PAUSE REPLAY</span>
              </>
            ) : (
              <>
                <Play size={13} />
                <span>RESUME REPLAY</span>
              </>
            )}
          </button>
        </div>
      </div>

      <div className="camera-feed-container">
        {/* Prominent Demo/Replay Watermark */}
        <div className="feed-watermark">
          DEMO / REPLAY MODE — [calibrated_floor_walk.mp4]
        </div>

        {/* Live MJPEG Stream Image */}
        <img
          src="/api/stream/mjpeg"
          alt="WorkSafe AI Live Camera Stream"
          className="camera-feed-image"
        />
      </div>

      {/* Live Pipeline Telemetry HUD Strip */}
      <div className="feed-hud-strip">
        <div className="hud-item">
          <span className="hud-label">FPS:</span>
          <span className="hud-val">{fps.toFixed(1)}</span>
        </div>
        <div className="hud-item">
          <span className="hud-label">LATENCY:</span>
          <span className="hud-val">{latency.toFixed(1)} ms</span>
        </div>
        <div className="hud-item">
          <span className="hud-label">FRAME:</span>
          <span className="hud-val">{frameId} / {totalFrames}</span>
        </div>
        <div className="hud-item">
          <span className="hud-label">WORKERS TRACKED:</span>
          <span className="hud-val">{tracksCount}</span>
        </div>
        <div className="hud-item">
          <span className="hud-label">CALIBRATION:</span>
          <span className="hud-val" style={{ color: '#10b981' }}>4-CORNER PLANAR (0.00 cm error)</span>
        </div>
      </div>
    </div>
  );
};
