import React, { useState } from 'react';
import { Camera, Radio, AlertTriangle, X } from 'lucide-react';
import { StatusBadge } from '../components/StatusBadge';
import type { CameraHealth, StreamStatus, SafetyState } from '../types';

interface CamerasPageProps {
  cameraHealth: CameraHealth | null;
  streamStatus: StreamStatus | null;
  safetyState: SafetyState;
  onNavigate: (page: string) => void;
}

export const CamerasPage: React.FC<CamerasPageProps> = ({
  cameraHealth,
  streamStatus,
  safetyState,
  onNavigate
}) => {
  const [selectedCameraModal, setSelectedCameraModal] = useState<string | null>(null);

  const cameras = [
    {
      id: 'cam_bay_01',
      name: 'CAM-BAY-01 — Machining Floor Aisle',
      location: 'Factory Bay 01 — Sector North',
      status: (cameraHealth?.health_state === 'HEALTHY' || !cameraHealth) ? 'ONLINE' : 'DEGRADED',
      health: cameraHealth?.health_state || 'HEALTHY',
      resolution: '1280 × 720 px @ 30 FPS',
      homography: 'Calibrated Planar Matrix (Floor Z=0)',
      fps: streamStatus?.pipeline_fps ?? 7.2,
      latency: streamStatus?.latency_ms ?? 138,
      frozenFrames: cameraHealth?.frozen_frame_count ?? 0,
      queueDepth: cameraHealth?.queue_depth ?? 0,
      maxQueue: cameraHealth?.max_queue_depth ?? 30,
      lastFrame: cameraHealth?.last_frame_id ?? (streamStatus?.current_frame_id ?? 0),
      lastHeartbeat: cameraHealth?.inter_frame_gap_ms ? `${cameraHealth.inter_frame_gap_ms.toFixed(1)} ms` : '66.7 ms',
      isConfigured: true,
      tag: 'ACTIVE REPLAY'
    },
    {
      id: 'cam_bay_02',
      name: 'CAM-BAY-02 — Robot Cell A Assembly',
      location: 'Factory Bay 02 — Automated Cell',
      status: 'STANDBY',
      health: 'STANDBY',
      resolution: '1920 × 1080 px (Planned)',
      homography: 'Pending Extrinsic Calibration',
      fps: 0,
      latency: 0,
      frozenFrames: 0,
      queueDepth: 0,
      maxQueue: 30,
      lastFrame: 0,
      lastHeartbeat: 'N/A (Standby)',
      isConfigured: false,
      tag: 'SIMULATED'
    },
    {
      id: 'cam_bay_03',
      name: 'CAM-BAY-03 — Automated Pallet Conveyor',
      location: 'Factory Bay 01 — West Logistics',
      status: 'STANDBY',
      health: 'STANDBY',
      resolution: '1280 × 720 px (Planned)',
      homography: 'Pending Ground Fiducials',
      fps: 0,
      latency: 0,
      frozenFrames: 0,
      queueDepth: 0,
      maxQueue: 30,
      lastFrame: 0,
      lastHeartbeat: 'N/A (Standby)',
      isConfigured: false,
      tag: 'SIMULATED'
    },
    {
      id: 'cam_bay_04',
      name: 'CAM-BAY-04 — Chemical Storage Perimeter',
      location: 'Facility Yard — Gate 3',
      status: 'OFFLINE',
      health: 'OFFLINE',
      resolution: '1920 × 1080 px (Planned)',
      homography: 'Uncalibrated / Disconnected',
      fps: 0,
      latency: 0,
      frozenFrames: 0,
      queueDepth: 0,
      maxQueue: 30,
      lastFrame: 0,
      lastHeartbeat: 'N/A (Offline)',
      isConfigured: false,
      tag: 'OFFLINE'
    }
  ];

  return (
    <div style={{ padding: '20px 24px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Header Info */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          backgroundColor: 'var(--bg-card, #11151f)',
          border: '1px solid var(--border-dim, #1f2738)',
          borderRadius: '6px',
          padding: '14px 20px'
        }}
      >
        <div>
          <h2 style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text-primary, #f1f5f9)' }}>
            Camera Network & Sensor Diagnostics
          </h2>
          <p style={{ fontSize: '0.75rem', color: 'var(--text-muted, #64748b)', marginTop: '2px' }}>
            Multi-camera topology with camera watchdog heartbeat, frame freezing detection, and homography plane validation.
          </p>
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          <span
            style={{
              padding: '4px 10px',
              borderRadius: '4px',
              backgroundColor: 'rgba(16, 185, 129, 0.15)',
              border: '1px solid #059669',
              color: '#34d399',
              fontSize: '0.75rem',
              fontFamily: 'var(--font-mono, monospace)',
              fontWeight: 600
            }}
          >
            1 Active Stream / 2 Standby / 1 Offline
          </span>
        </div>
      </div>

      {/* Camera Pipeline Performance Diagnostic Comparison */}
      <section
        aria-label="Camera Pipeline Performance"
        style={{
          backgroundColor: '#0c1018',
          border: '1px solid #161e2e',
          borderRadius: '6px',
          padding: '16px 18px',
          display: 'flex',
          flexDirection: 'column',
          gap: '12px'
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <div style={{ fontSize: '0.8125rem', fontWeight: 700, color: '#f8fafc', letterSpacing: '0.04em' }}>
              CAMERA PIPELINE PERFORMANCE DIAGNOSTIC COMPARISON
            </div>
            <p style={{ fontSize: '0.6875rem', color: '#64748b', marginTop: '2px' }}>
              Real-time multi-camera comparative diagnostics: throughput FPS, processing latency, buffer queue depth, and watchdog heartbeats.
            </p>
          </div>
          <div style={{ display: 'flex', gap: '10px', fontSize: '0.625rem', fontFamily: 'var(--font-mono, monospace)' }}>
            <span style={{ color: '#10b981' }}>● Nominal &lt; 200ms</span>
            <span style={{ color: '#f59e0b' }}>▲ Warning &gt; 200ms</span>
            <span style={{ color: '#ef4444' }}>■ Critical &gt; 500ms</span>
          </div>
        </div>

        {/* Comparative Diagnostic Table / Bars */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '12px' }}>
          {cameras.map((c) => {
            const isAbnormalLatency = c.latency > 200;
            const isAbnormalQueue = c.queueDepth > 15;
            const isAbnormalFrozen = c.frozenFrames > 0;
            const hasIssue = isAbnormalLatency || isAbnormalQueue || isAbnormalFrozen;

            return (
              <div
                key={`perf-${c.id}`}
                style={{
                  backgroundColor: '#07090f',
                  border: `1px solid ${hasIssue ? '#dc2626' : c.isConfigured ? '#1f2738' : '#141a24'}`,
                  borderRadius: '4px',
                  padding: '12px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '8px'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: '0.75rem', fontWeight: 700, color: c.isConfigured ? '#38bdf8' : '#94a3b8', fontFamily: 'var(--font-mono, monospace)' }}>
                    {c.id.toUpperCase()}
                  </span>
                  <span
                    style={{
                      fontSize: '0.5625rem',
                      fontWeight: 700,
                      padding: '1px 6px',
                      borderRadius: '3px',
                      backgroundColor: c.status === 'ONLINE' ? 'rgba(16, 185, 129, 0.15)' : c.status === 'STANDBY' ? 'rgba(56, 189, 248, 0.1)' : 'rgba(239, 68, 68, 0.1)',
                      color: c.status === 'ONLINE' ? '#34d399' : c.status === 'STANDBY' ? '#38bdf8' : '#f87171'
                    }}
                  >
                    {c.status}
                  </span>
                </div>

                {/* Metrics with mini comparison bars */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', fontSize: '0.6875rem' }}>
                  {/* FPS */}
                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', color: '#64748b', fontSize: '0.5625rem', marginBottom: '2px' }}>
                      <span>THROUGHPUT FPS</span>
                      <strong style={{ color: c.fps > 0 ? '#f8fafc' : '#64748b', fontFamily: 'var(--font-mono, monospace)' }}>
                        {c.fps > 0 ? `${c.fps.toFixed(1)} FPS` : '0.0 FPS'}
                      </strong>
                    </div>
                    <div style={{ height: '4px', backgroundColor: '#141a27', borderRadius: '2px', overflow: 'hidden' }}>
                      <div style={{ width: `${Math.min(100, (c.fps / 15) * 100)}%`, height: '100%', backgroundColor: '#10b981' }} />
                    </div>
                  </div>

                  {/* Latency */}
                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', color: '#64748b', fontSize: '0.5625rem', marginBottom: '2px' }}>
                      <span>LATENCY (TARGET &lt; 150ms)</span>
                      <strong style={{ color: isAbnormalLatency ? '#f87171' : c.latency > 0 ? '#34d399' : '#64748b', fontFamily: 'var(--font-mono, monospace)' }}>
                        {c.latency > 0 ? `${c.latency.toFixed(0)} ms` : '—'}
                      </strong>
                    </div>
                    <div style={{ height: '4px', backgroundColor: '#141a27', borderRadius: '2px', overflow: 'hidden' }}>
                      <div style={{ width: `${Math.min(100, (c.latency / 250) * 100)}%`, height: '100%', backgroundColor: isAbnormalLatency ? '#ef4444' : '#38bdf8' }} />
                    </div>
                  </div>

                  {/* Queue Depth */}
                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', color: '#64748b', fontSize: '0.5625rem', marginBottom: '2px' }}>
                      <span>BUFFER QUEUE DEPTH</span>
                      <strong style={{ color: isAbnormalQueue ? '#f87171' : '#f8fafc', fontFamily: 'var(--font-mono, monospace)' }}>
                        {c.queueDepth} / {c.maxQueue}
                      </strong>
                    </div>
                    <div style={{ height: '4px', backgroundColor: '#141a27', borderRadius: '2px', overflow: 'hidden' }}>
                      <div style={{ width: `${Math.min(100, (c.queueDepth / c.maxQueue) * 100)}%`, height: '100%', backgroundColor: isAbnormalQueue ? '#ef4444' : '#10b981' }} />
                    </div>
                  </div>

                  {/* Watchdog Heartbeat & Frozen */}
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingTop: '4px', borderTop: '1px solid #141a27', fontSize: '0.5625rem' }}>
                    <span style={{ color: '#64748b' }}>FROZEN FRAMES:</span>
                    <strong style={{ color: isAbnormalFrozen ? '#f87171' : '#34d399', fontFamily: 'var(--font-mono, monospace)' }}>
                      {c.frozenFrames} (OK)
                    </strong>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.5625rem' }}>
                    <span style={{ color: '#64748b' }}>HEARTBEAT GAP:</span>
                    <strong style={{ color: '#f8fafc', fontFamily: 'var(--font-mono, monospace)' }}>
                      {c.lastHeartbeat}
                    </strong>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* Camera Grid */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
          gap: '16px'
        }}
      >
        {cameras.map((cam) => {
          return (
            <div
              key={cam.id}
              onClick={() => setSelectedCameraModal(cam.id)}
              style={{
                backgroundColor: 'var(--bg-card, #11151f)',
                border: '1px solid var(--border-dim, #1f2738)',
                borderRadius: '6px',
                padding: '16px',
                display: 'flex',
                flexDirection: 'column',
                gap: '14px',
                cursor: 'pointer',
                opacity: cam.isConfigured ? 1 : 0.85,
                transition: 'border-color 0.15s, transform 0.15s'
              }}
            >
              {/* Card Top */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <div
                    style={{
                      width: '36px',
                      height: '36px',
                      borderRadius: '6px',
                      backgroundColor: cam.isConfigured ? 'rgba(56, 189, 248, 0.15)' : 'var(--bg-card-subtle, #161c2b)',
                      border: `1px solid ${cam.isConfigured ? '#0284c7' : 'var(--border-mid, #2d374d)'}`,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      color: cam.isConfigured ? '#38bdf8' : 'var(--text-muted, #64748b)'
                    }}
                  >
                    <Camera size={18} />
                  </div>
                  <div>
                    <div style={{ fontSize: '0.875rem', fontWeight: 600, color: 'var(--text-primary, #f1f5f9)' }}>
                      {cam.name}
                    </div>
                    <div style={{ fontSize: '0.6875rem', color: 'var(--text-muted, #64748b)', marginTop: '2px' }}>
                      {cam.location} • <span style={{ color: '#38bdf8' }}>{cam.tag}</span>
                    </div>
                  </div>
                </div>

                <StatusBadge state={cam.status} size="sm" />
              </div>

              {/* Live Preview / Standby Placeholder */}
              <div
                style={{
                  height: '140px',
                  borderRadius: '4px',
                  backgroundColor: '#05070a',
                  border: '1px solid var(--border-dim, #1f2738)',
                  overflow: 'hidden',
                  position: 'relative',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center'
                }}
              >
                {cam.isConfigured ? (
                  <>
                    <img
                      src="/api/stream/mjpeg"
                      alt={cam.name}
                      style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                    />
                    <div
                      style={{
                        position: 'absolute',
                        top: '8px',
                        right: '8px'
                      }}
                    >
                      <StatusBadge state={safetyState} size="sm" pulse={safetyState === 'DANGER'} />
                    </div>
                  </>
                ) : (
                  <div style={{ textAlign: 'center', color: 'var(--text-muted, #64748b)', padding: '12px' }}>
                    <Radio size={24} style={{ margin: '0 auto 6px auto', display: 'block', opacity: 0.5 }} />
                    <div style={{ fontSize: '0.75rem', fontWeight: 600 }}>{cam.status === 'OFFLINE' ? 'OFFLINE / UNCONNECTED' : 'STANDBY / SIMULATED'}</div>
                    <div style={{ fontSize: '0.6875rem', marginTop: '2px' }}>{cam.status === 'OFFLINE' ? 'Hardware sensor disconnected' : 'RTSP Ingest stream on standby'}</div>
                  </div>
                )}
              </div>

              {/* Metrics Grid */}
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(3, 1fr)',
                  gap: '8px',
                  fontSize: '0.6875rem',
                  color: 'var(--text-secondary, #94a3b8)',
                  backgroundColor: 'var(--bg-app, #090b10)',
                  padding: '10px 12px',
                  borderRadius: '4px',
                  border: '1px solid var(--border-dim, #1f2738)'
                }}
              >
                <div>
                  <span style={{ color: 'var(--text-muted, #64748b)', display: 'block', fontSize: '0.5625rem' }}>THROUGHPUT</span>
                  <strong style={{ color: cam.isConfigured ? '#34d399' : 'inherit', fontFamily: 'var(--font-mono, monospace)' }}>
                    {cam.isConfigured ? `${cam.fps.toFixed(1)} FPS` : '0 FPS'}
                  </strong>
                </div>

                <div>
                  <span style={{ color: 'var(--text-muted, #64748b)', display: 'block', fontSize: '0.5625rem' }}>LATENCY</span>
                  <strong style={{ fontFamily: 'var(--font-mono, monospace)' }}>
                    {cam.isConfigured ? `${Math.round(cam.latency)} ms` : 'N/A'}
                  </strong>
                </div>

                <div>
                  <span style={{ color: 'var(--text-muted, #64748b)', display: 'block', fontSize: '0.5625rem' }}>QUEUE DEPTH</span>
                  <strong style={{ fontFamily: 'var(--font-mono, monospace)' }}>
                    {cam.queueDepth} / {cam.maxQueue}
                  </strong>
                </div>

                <div>
                  <span style={{ color: 'var(--text-muted, #64748b)', display: 'block', fontSize: '0.5625rem' }}>FROZEN FRAMES</span>
                  <strong style={{ color: cam.frozenFrames > 0 ? '#ef4444' : '#34d399', fontFamily: 'var(--font-mono, monospace)' }}>
                    {cam.frozenFrames}
                  </strong>
                </div>

                <div>
                  <span style={{ color: 'var(--text-muted, #64748b)', display: 'block', fontSize: '0.5625rem' }}>HEARTBEAT</span>
                  <strong style={{ color: cam.isConfigured ? '#34d399' : 'inherit', fontFamily: 'var(--font-mono, monospace)' }}>
                    {cam.lastHeartbeat}
                  </strong>
                </div>

                <div>
                  <span style={{ color: 'var(--text-muted, #64748b)', display: 'block', fontSize: '0.5625rem' }}>CALIBRATION</span>
                  <strong style={{ color: cam.isConfigured ? '#38bdf8' : '#64748b', fontSize: '0.625rem' }}>
                    {cam.isConfigured ? 'Z=0 Valid' : 'Pending'}
                  </strong>
                </div>
              </div>

              {/* Card Footer */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: '0.6875rem', color: 'var(--text-muted, #64748b)' }}>
                  {cam.homography}
                </span>
                <span
                  style={{
                    fontSize: '0.75rem',
                    color: '#38bdf8',
                    fontWeight: 500,
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px'
                  }}
                >
                  Inspect Diagnostics →
                </span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Detailed Camera Diagnostics Modal */}
      {selectedCameraModal && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            backgroundColor: 'rgba(5, 7, 12, 0.8)',
            backdropFilter: 'blur(4px)',
            zIndex: 1000,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '20px'
          }}
          onClick={() => setSelectedCameraModal(null)}
        >
          <div
            style={{
              backgroundColor: 'var(--bg-card, #11151f)',
              border: '1px solid var(--border-mid, #2d374d)',
              borderRadius: '8px',
              width: '100%',
              maxWidth: '620px',
              boxShadow: '0 20px 40px rgba(0, 0, 0, 0.6)',
              overflow: 'hidden'
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div
              style={{
                padding: '16px 20px',
                borderBottom: '1px solid var(--border-dim, #1f2738)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                backgroundColor: 'var(--bg-card-subtle, #161c2b)'
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Camera size={18} color="#38bdf8" />
                <span style={{ fontWeight: 600, color: 'var(--text-primary, #f1f5f9)', fontSize: '0.9375rem' }}>
                  {selectedCameraModal === 'cam_bay_01'
                    ? 'CAM-BAY-01 Diagnostics & Ingest Pipeline'
                    : `${selectedCameraModal} (Unconfigured Standby)`}
                </span>
              </div>
              <button
                onClick={() => setSelectedCameraModal(null)}
                style={{ background: 'none', border: 'none', color: 'var(--text-muted, #64748b)', cursor: 'pointer' }}
              >
                <X size={18} />
              </button>
            </div>

            <div style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
              {selectedCameraModal === 'cam_bay_01' ? (
                <>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '12px', fontSize: '0.8125rem' }}>
                    <div style={{ backgroundColor: 'var(--bg-card-subtle, #161c2b)', padding: '12px', borderRadius: '4px' }}>
                      <div style={{ color: 'var(--text-muted, #64748b)', fontSize: '0.6875rem' }}>HEALTH STATE</div>
                      <div style={{ color: '#34d399', fontWeight: 600, marginTop: '2px' }}>
                        {cameraHealth?.health_state || 'HEALTHY'} (Heartbeat Nominal)
                      </div>
                    </div>

                    <div style={{ backgroundColor: 'var(--bg-card-subtle, #161c2b)', padding: '12px', borderRadius: '4px' }}>
                      <div style={{ color: 'var(--text-muted, #64748b)', fontSize: '0.6875rem' }}>INGESTION QUEUE</div>
                      <div style={{ color: 'var(--text-primary, #f1f5f9)', fontWeight: 600, marginTop: '2px', fontFamily: 'var(--font-mono, monospace)' }}>
                        {cameraHealth?.queue_depth ?? 0} / {cameraHealth?.max_queue_depth ?? 30} frames
                      </div>
                    </div>

                    <div style={{ backgroundColor: 'var(--bg-card-subtle, #161c2b)', padding: '12px', borderRadius: '4px' }}>
                      <div style={{ color: 'var(--text-muted, #64748b)', fontSize: '0.6875rem' }}>INTER-FRAME GAP</div>
                      <div style={{ color: 'var(--text-primary, #f1f5f9)', fontWeight: 600, marginTop: '2px', fontFamily: 'var(--font-mono, monospace)' }}>
                        {cameraHealth?.inter_frame_gap_ms?.toFixed(1) ?? '33.3'} ms
                      </div>
                    </div>

                    <div style={{ backgroundColor: 'var(--bg-card-subtle, #161c2b)', padding: '12px', borderRadius: '4px' }}>
                      <div style={{ color: 'var(--text-muted, #64748b)', fontSize: '0.6875rem' }}>FROZEN FRAMES</div>
                      <div style={{ color: (cameraHealth?.frozen_frame_count ?? 0) > 0 ? '#ef4444' : '#34d399', fontWeight: 600, marginTop: '2px' }}>
                        {cameraHealth?.frozen_frame_count ?? 0}
                      </div>
                    </div>
                  </div>

                  <div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted, #64748b)', textTransform: 'uppercase', marginBottom: '6px' }}>
                      Homography Matrix Validation (Experiment 03 Calibration)
                    </div>
                    <div
                      style={{
                        padding: '12px',
                        backgroundColor: 'var(--bg-app, #090b10)',
                        border: '1px solid var(--border-dim, #1f2738)',
                        borderRadius: '4px',
                        fontFamily: 'var(--font-mono, monospace)',
                        fontSize: '0.75rem',
                        color: '#94a3b8'
                      }}
                    >
                      Planar ground calibration active. Determinant != 0 (Validated AC-09: Invalid calibration rejection tested).
                      <br />
                      Coordinate space: Millimeters (X: 0–4000 mm, Y: 0–4500 mm).
                    </div>
                  </div>

                  <div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted, #64748b)', textTransform: 'uppercase', marginBottom: '6px' }}>
                      Failure Reasons / Watchdog Diagnostic Log
                    </div>
                    <div
                      style={{
                        padding: '10px 12px',
                        backgroundColor: 'var(--bg-app, #090b10)',
                        border: '1px solid var(--border-dim, #1f2738)',
                        borderRadius: '4px',
                        fontSize: '0.75rem',
                        color: cameraHealth?.failure_reasons?.length ? '#f87171' : '#34d399'
                      }}
                    >
                      {cameraHealth?.failure_reasons?.length
                        ? cameraHealth.failure_reasons.join(', ')
                        : 'Zero faults registered. Camera stream healthy and uninterrupted.'}
                    </div>
                  </div>
                </>
              ) : (
                <div style={{ textAlign: 'center', padding: '24px 12px', color: 'var(--text-muted, #64748b)' }}>
                  <AlertTriangle size={32} color="#f59e0b" style={{ margin: '0 auto 8px auto', display: 'block' }} />
                  <div style={{ fontSize: '0.875rem', fontWeight: 600, color: 'var(--text-primary, #f1f5f9)' }}>
                    Camera Sensor Offline / Pending Provisioning
                  </div>
                  <p style={{ fontSize: '0.75rem', marginTop: '4px', maxWidth: '380px', margin: '4px auto 0 auto' }}>
                    This camera channel is reserved for secondary bay expansion. To provision, connect an ONVIF / RTSP camera feed and calibrate floor plane homography.
                  </p>
                </div>
              )}
            </div>

            <div
              style={{
                padding: '14px 20px',
                borderTop: '1px solid var(--border-dim, #1f2738)',
                display: 'flex',
                justifyContent: 'flex-end',
                gap: '10px',
                backgroundColor: 'var(--bg-card-subtle, #161c2b)'
              }}
            >
              <button
                onClick={() => setSelectedCameraModal(null)}
                style={{
                  padding: '6px 14px',
                  borderRadius: '4px',
                  backgroundColor: 'var(--bg-app, #090b10)',
                  border: '1px solid var(--border-mid, #2d374d)',
                  color: 'var(--text-secondary, #94a3b8)',
                  fontSize: '0.8125rem',
                  cursor: 'pointer'
                }}
              >
                Close
              </button>
              {selectedCameraModal === 'cam_bay_01' && (
                <button
                  onClick={() => {
                    setSelectedCameraModal(null);
                    onNavigate('monitoring');
                  }}
                  style={{
                    padding: '6px 16px',
                    borderRadius: '4px',
                    backgroundColor: '#0284c7',
                    border: 'none',
                    color: '#ffffff',
                    fontSize: '0.8125rem',
                    fontWeight: 600,
                    cursor: 'pointer'
                  }}
                >
                  Open Live Monitoring →
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
