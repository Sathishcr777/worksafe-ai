import React, { useState } from 'react';
import {
  Settings,
  Lock,
  Shield,
  Camera,
  Sliders,
  Database,
  Server,
  AlertTriangle,
  Search,
  CheckCircle,
  HelpCircle,
  Cpu
} from 'lucide-react';

type ParamStatus = 'CONFIGURED' | 'READ_ONLY' | 'LOCKED' | 'DEMO';

interface SettingItem {
  id: string;
  label: string;
  description: string;
  value: string;
  status: ParamStatus;
  category: 'safety' | 'vision' | 'hardware' | 'compliance';
}

export const SettingsPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'all' | 'safety' | 'vision' | 'hardware' | 'compliance'>('all');
  const [searchQuery, setSearchQuery] = useState('');

  const settings: SettingItem[] = [
    // Safety & Temporal
    {
      id: 'param-danger-poly',
      label: 'Danger Zone 01 Polygon',
      description: 'Physical mm coordinates defining the forbidden zone on the calibrated floor plane.',
      value: '[(1000, 2000), (3000, 2000), (3000, 4500), (1000, 4500)] mm',
      status: 'CONFIGURED',
      category: 'safety'
    },
    {
      id: 'param-warning-buf',
      label: 'Warning Buffer Offset',
      description: 'Perimeter expansion distance around danger zones where warnings are issued.',
      value: '+500 mm expansion perimeter',
      status: 'CONFIGURED',
      category: 'safety'
    },
    {
      id: 'param-breach-debounce',
      label: 'Danger Breach Hysteresis Debounce',
      description: 'Consecutive positive detection frames required before latching into DANGER state.',
      value: '3 Consecutive Frames (~100 ms at 30 FPS)',
      status: 'CONFIGURED',
      category: 'safety'
    },
    {
      id: 'param-warning-debounce',
      label: 'Warning Buffer Hysteresis Debounce',
      description: 'Consecutive positive detection frames required before latching into WARNING state.',
      value: '2 Consecutive Frames (~66 ms at 30 FPS)',
      status: 'CONFIGURED',
      category: 'safety'
    },
    {
      id: 'param-recovery-debounce',
      label: 'Monotonic Recovery Countdown',
      description: 'Continuous safe frames required before transitioning out of DANGER / WARNING.',
      value: '30 Consecutive Safe Frames (1.000 s)',
      status: 'CONFIGURED',
      category: 'safety'
    },
    {
      id: 'param-ground-contact',
      label: 'Worker Ground Contact Anchor',
      description: 'Bounding box keypoint mapped through homography matrix H to ground plane Z=0.',
      value: 'Midpoint Bottom Bounding Box (x_mid, y2)',
      status: 'CONFIGURED',
      category: 'safety'
    },

    // Compliance & Supervisory Locks
    {
      id: 'param-estop-interlock',
      label: 'E-Stop Machinery Interlock',
      description: 'Direct contactor cut is prohibited. WorkSafe AI operates as supervisory advisory layer only.',
      value: 'SUPERVISORY ADVISORY ONLY (No Direct Contactor Trip)',
      status: 'LOCKED',
      category: 'compliance'
    },
    {
      id: 'param-iso-compliance',
      label: 'Functional Safety Rating Boundary',
      description: 'Non-SIL software system under ISO 13849-1 / IEC 62061. Certified hardware safety mats/curtains required.',
      value: 'ISO 13849-1 Non-SIL Supervisory Assistant',
      status: 'LOCKED',
      category: 'compliance'
    },
    {
      id: 'param-fail-safe-rule',
      label: 'Conservative Fail-Safe State',
      description: 'Behavior when video ingestion stalls or camera frame rate drops below watchdog threshold.',
      value: 'FAIL_TO_DANGER (Immediate SYSTEM UNKNOWN Alarm)',
      status: 'LOCKED',
      category: 'compliance'
    },
    {
      id: 'param-privacy-obfuscation',
      label: 'Facial Obfuscation Policy',
      description: 'Strict zero-biometrics guarantee. Head ROI is blurred in memory before stream broadcast.',
      value: 'Top 25% BBox ROI Gaussian Blur (31×31, σ=10.0)',
      status: 'LOCKED',
      category: 'compliance'
    },
    {
      id: 'param-zero-pii',
      label: 'Biometric Vector Storage',
      description: 'Storage of facial encodings, worker names, or facial landmarks is permanently disabled.',
      value: 'STRICTLY PROHIBITED (Zero Biometrics Stored)',
      status: 'LOCKED',
      category: 'compliance'
    },

    // Vision & Camera
    {
      id: 'param-primary-cam',
      label: 'Primary Ingestion Camera',
      description: 'Industrial RTSP/File feed delivering raw machine bay footage to the worker detection worker.',
      value: 'CAM-BAY-01 (industrial_factory_demo.mp4)',
      status: 'READ_ONLY',
      category: 'vision'
    },
    {
      id: 'param-cam-resolution',
      label: 'Native Video Resolution & Framing',
      description: 'Ingestion frame geometry and framerate negotiated with camera sensor.',
      value: '1280 × 720 px @ 30.0 FPS (Multipart MJPEG)',
      status: 'READ_ONLY',
      category: 'vision'
    },
    {
      id: 'param-homography-h',
      label: 'Planar Homography Calibration Matrix H',
      description: 'Calculated from 4 surveyed ground survey points. Verified det(H) > 1e-6 non-singular.',
      value: '3×3 Projective Matrix [H11..H33] (Factory Datum Z=0)',
      status: 'READ_ONLY',
      category: 'vision'
    },
    {
      id: 'param-frozen-frame',
      label: 'Frozen Frame Watchdog Detector',
      description: 'Laplacian variance threshold between consecutive frames to detect frozen camera encoders.',
      value: 'Laplacian Variance < 2.0 (Threshold Trigger)',
      status: 'READ_ONLY',
      category: 'vision'
    },
    {
      id: 'param-queue-strategy',
      label: 'Lossy Ingestion Queue Capacity',
      description: 'Bounded FIFO queue preventing latency accumulation when inference load spikes.',
      value: '30 Frames (Drop-Oldest Strategy, Max Latency 1000ms)',
      status: 'READ_ONLY',
      category: 'vision'
    },

    // Hardware & AI Infrastructure
    {
      id: 'param-detector-model',
      label: 'Neural Detector Architecture',
      description: 'Deep learning weights and input dimension for person bounding box localization.',
      value: 'Ultralytics YOLOv8n (PyTorch CPU, 640×640)',
      status: 'READ_ONLY',
      category: 'hardware'
    },
    {
      id: 'param-tracker-backend',
      label: 'Multi-Object Tracking Algorithm',
      description: 'Associates detections across time with Kalman state filter and 2-stage IoU cost matrix.',
      value: 'ByteTrack (track_thresh=0.5, track_buffer=30)',
      status: 'READ_ONLY',
      category: 'hardware'
    },
    {
      id: 'param-database-engine',
      label: 'Relational Event Store',
      description: 'ACID transactional audit storage with Write-Ahead-Logging for non-blocking concurrent writes.',
      value: 'SQLite 3 (PRAGMA journal_mode = WAL, synchronous = NORMAL)',
      status: 'READ_ONLY',
      category: 'hardware'
    },
    {
      id: 'param-dedup-window',
      label: 'Event Deduplication Engine',
      description: 'Suppresses duplicate safety violation records during prolonged hazard exposures.',
      value: 'In-Memory State Key Hash (10.0 s cooldown)',
      status: 'READ_ONLY',
      category: 'hardware'
    },

    // Demo & Simulation
    {
      id: 'param-demo-loop',
      label: 'Synthetic Stream Loop Mode',
      description: 'Automatically rewinds the demonstration stream to frame 0 upon reaching end of file.',
      value: 'ENABLED (Loop at frame 540)',
      status: 'DEMO',
      category: 'vision'
    },
    {
      id: 'param-demo-scrubber',
      label: 'Interactive Replay Scrubber',
      description: 'Allows supervisory operator to seek pipeline backward/forward for post-incident analysis.',
      value: 'ENABLED (POST /api/demo/seek endpoint)',
      status: 'DEMO',
      category: 'hardware'
    }
  ];

  const getStatusBadge = (status: ParamStatus) => {
    switch (status) {
      case 'LOCKED':
        return (
          <span
            style={{
              padding: '2px 8px',
              borderRadius: '4px',
              backgroundColor: 'rgba(239, 68, 68, 0.15)',
              border: '1px solid rgba(239, 68, 68, 0.4)',
              color: '#f87171',
              fontSize: '0.625rem',
              fontFamily: 'var(--font-mono, monospace)',
              fontWeight: 700,
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px'
            }}
          >
            <Lock size={10} />
            LOCKED / SUPERVISORY ONLY
          </span>
        );
      case 'CONFIGURED':
        return (
          <span
            style={{
              padding: '2px 8px',
              borderRadius: '4px',
              backgroundColor: 'rgba(16, 185, 129, 0.15)',
              border: '1px solid rgba(16, 185, 129, 0.4)',
              color: '#34d399',
              fontSize: '0.625rem',
              fontFamily: 'var(--font-mono, monospace)',
              fontWeight: 700,
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px'
            }}
          >
            <CheckCircle size={10} />
            CONFIGURED / ACTIVE
          </span>
        );
      case 'READ_ONLY':
        return (
          <span
            style={{
              padding: '2px 8px',
              borderRadius: '4px',
              backgroundColor: 'rgba(56, 189, 248, 0.12)',
              border: '1px solid rgba(56, 189, 248, 0.35)',
              color: '#38bdf8',
              fontSize: '0.625rem',
              fontFamily: 'var(--font-mono, monospace)',
              fontWeight: 700,
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px'
            }}
          >
            <Sliders size={10} />
            READ ONLY / HARDWARE LINKED
          </span>
        );
      case 'DEMO':
        return (
          <span
            style={{
              padding: '2px 8px',
              borderRadius: '4px',
              backgroundColor: 'rgba(168, 85, 247, 0.15)',
              border: '1px solid rgba(168, 85, 247, 0.4)',
              color: '#c084fc',
              fontSize: '0.625rem',
              fontFamily: 'var(--font-mono, monospace)',
              fontWeight: 700,
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px'
            }}
          >
            <Cpu size={10} />
            DEMO / MOCKABLE
          </span>
        );
    }
  };

  const filtered = settings.filter((item) => {
    const matchesTab = activeTab === 'all' || item.category === activeTab;
    const matchesQuery =
      searchQuery.trim() === '' ||
      item.label.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.value.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.status.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesTab && matchesQuery;
  });

  return (
    <div style={{ padding: '20px 24px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Header Info */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          backgroundColor: '#0c1018',
          border: '1px solid #161e2e',
          borderRadius: '6px',
          padding: '16px 20px',
          flexWrap: 'wrap',
          gap: '12px'
        }}
      >
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Settings size={18} color="#38bdf8" />
            <h2 style={{ fontSize: '1.0625rem', fontWeight: 600, color: '#f8fafc' }}>
              System Configuration & Operating Parameters
            </h2>
          </div>
          <p style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '2px' }}>
            Verified operating thresholds, temporal debouncing constants, sensor calibrations, and functional safety constraints.
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span
            style={{
              padding: '4px 10px',
              borderRadius: '4px',
              backgroundColor: 'rgba(239, 68, 68, 0.15)',
              border: '1px solid #dc2626',
              color: '#f87171',
              fontSize: '0.75rem',
              fontFamily: 'var(--font-mono, monospace)',
              fontWeight: 600,
              display: 'flex',
              alignItems: 'center',
              gap: '6px'
            }}
          >
            <Lock size={12} />
            CRITICAL SAFETY PARAMS LOCKED
          </span>
        </div>
      </div>

      {/* Safety Policy Banner */}
      <div
        style={{
          backgroundColor: 'rgba(245, 158, 11, 0.08)',
          border: '1px solid rgba(245, 158, 11, 0.3)',
          borderRadius: '6px',
          padding: '12px 16px',
          display: 'flex',
          alignItems: 'flex-start',
          gap: '12px'
        }}
      >
        <AlertTriangle size={18} color="#f59e0b" style={{ flexShrink: 0, marginTop: '2px' }} />
        <div style={{ fontSize: '0.75rem', color: '#cbd5e1', lineHeight: '1.4' }}>
          <strong style={{ color: '#f59e0b' }}>Supervisory Architecture Policy Notice:</strong> Safety-critical geometric boundaries and temporal hysteresis constants cannot be modified while monitoring is active. Modifying zone polygons or debounce filters requires stopping the stream, physical site re-survey, and dual-operator engineering authorization.
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          gap: '16px',
          flexWrap: 'wrap'
        }}
      >
        {/* Category Tabs */}
        <div style={{ display: 'flex', gap: '6px' }}>
          {[
            { key: 'all', label: 'All Parameters', icon: <Server size={13} /> },
            { key: 'safety', label: 'Safety & Debounce', icon: <Shield size={13} /> },
            { key: 'compliance', label: 'Compliance & Locks', icon: <Lock size={13} /> },
            { key: 'vision', label: 'Vision & Camera', icon: <Camera size={13} /> },
            { key: 'hardware', label: 'Hardware & AI', icon: <Database size={13} /> }
          ].map((tab) => {
            const isActive = activeTab === tab.key;
            return (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key as any)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  padding: '6px 12px',
                  borderRadius: '4px',
                  fontSize: '0.75rem',
                  fontWeight: 600,
                  backgroundColor: isActive ? '#1e293b' : '#0c1018',
                  color: isActive ? '#38bdf8' : '#64748b',
                  border: isActive ? '1px solid #38bdf8' : '1px solid #161e2e',
                  cursor: 'pointer',
                  transition: 'all 0.15s ease'
                }}
              >
                {tab.icon}
                {tab.label}
              </button>
            );
          })}
        </div>

        {/* Search Input */}
        <div style={{ position: 'relative', width: '280px' }}>
          <Search
            size={14}
            color="#64748b"
            style={{ position: 'absolute', left: '10px', top: '50%', transform: 'translateY(-50%)' }}
          />
          <input
            type="text"
            placeholder="Search parameters or status..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{
              width: '100%',
              padding: '6px 12px 6px 32px',
              backgroundColor: '#0c1018',
              border: '1px solid #161e2e',
              borderRadius: '4px',
              color: '#f8fafc',
              fontSize: '0.75rem',
              outline: 'none'
            }}
          />
        </div>
      </div>

      {/* Status Legend */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '16px',
          padding: '8px 14px',
          backgroundColor: '#0a0e17',
          borderRadius: '4px',
          border: '1px solid #141b27',
          fontSize: '0.6875rem',
          color: '#64748b',
          flexWrap: 'wrap'
        }}
      >
        <span style={{ fontWeight: 600, color: '#94a3b8' }}>Status Taxonomy:</span>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <div style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: '#10b981' }} />
          <span>CONFIGURED (Operating parameter active)</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <div style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: '#38bdf8' }} />
          <span>READ ONLY (Fixed by hardware/model)</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <div style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: '#ef4444' }} />
          <span>LOCKED (Functional safety constraint)</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <div style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: '#a855f7' }} />
          <span>DEMO (Simulation / Mockable feature)</span>
        </div>
      </div>

      {/* Settings Grid */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(420px, 1fr))',
          gap: '12px'
        }}
      >
        {filtered.map((item) => (
          <div
            key={item.id}
            style={{
              backgroundColor: '#0c1018',
              border: '1px solid #161e2e',
              borderRadius: '6px',
              padding: '14px 16px',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
              gap: '12px'
            }}
          >
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '8px' }}>
                <span style={{ fontSize: '0.8125rem', fontWeight: 600, color: '#f8fafc' }}>
                  {item.label}
                </span>
                {getStatusBadge(item.status)}
              </div>
              <p style={{ fontSize: '0.6875rem', color: '#64748b', marginTop: '4px', lineHeight: '1.4' }}>
                {item.description}
              </p>
            </div>

            <div
              style={{
                backgroundColor: '#070a10',
                border: '1px solid #141b27',
                borderRadius: '4px',
                padding: '8px 10px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                gap: '8px'
              }}
            >
              <code
                style={{
                  fontFamily: 'var(--font-mono, monospace)',
                  fontSize: '0.6875rem',
                  color: item.status === 'LOCKED' ? '#f87171' : item.status === 'CONFIGURED' ? '#34d399' : '#38bdf8',
                  wordBreak: 'break-all'
                }}
              >
                {item.value}
              </code>
              <HelpCircle size={13} color="#475569" style={{ flexShrink: 0 }} />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
