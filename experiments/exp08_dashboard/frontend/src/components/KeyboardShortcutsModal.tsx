import React from 'react';
import { Keyboard, X } from 'lucide-react';

interface KeyboardShortcutsModalProps {
  onClose: () => void;
}

export const KeyboardShortcutsModal: React.FC<KeyboardShortcutsModalProps> = ({ onClose }) => {
  const shortcuts = [
    {
      category: 'Pipeline & Playback',
      items: [
        { keys: ['Space'], desc: 'Toggle Play / Pause pipeline stream' },
        { keys: ['R'], desc: 'Restart demo playback from frame 0' },
        { keys: ['Esc'], desc: 'Dismiss active modals or drawers' },
        { keys: ['?'], desc: 'Toggle this keyboard shortcuts dialog' }
      ]
    },
    {
      category: 'Direct Page Navigation (Number Keys)',
      items: [
        { keys: ['1'], desc: 'Command Center (Triage & Multi-Bay Overview)' },
        { keys: ['2'], desc: 'Live Monitoring (Full Telemetry & Ground Plane)' },
        { keys: ['3'], desc: 'Cameras (Network & Ingestion Health)' },
        { keys: ['4'], desc: 'Active Alerts (Triage & TTA)' },
        { keys: ['5'], desc: 'Event History (Historical Audit Trail)' },
        { keys: ['6'], desc: 'Analytics (MTTR, Hazard Exposure, Detections)' },
        { keys: ['7'], desc: 'System Health (Subsystem Latencies & Profiling)' },
        { keys: ['8'], desc: 'Replay Scenarios (Incident Scrubber & Jumps)' },
        { keys: ['9'], desc: 'Safety Reports (Executive Summary & Export)' },
        { keys: ['0'], desc: 'Settings (Operating Boundaries & Rules)' }
      ]
    }
  ];

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(5, 7, 12, 0.82)',
        backdropFilter: 'blur(4px)',
        zIndex: 100,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '20px'
      }}
      onClick={onClose}
    >
      <div
        style={{
          width: '100%',
          maxWidth: '560px',
          backgroundColor: '#0c1018',
          border: '1px solid #1e293b',
          borderRadius: '8px',
          boxShadow: '0 20px 40px rgba(0, 0, 0, 0.6), 0 0 0 1px rgba(56, 189, 248, 0.1)',
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'column'
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div
          style={{
            padding: '14px 18px',
            backgroundColor: '#0f1420',
            borderBottom: '1px solid #161e2e',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Keyboard size={18} color="#38bdf8" />
            <h3 style={{ fontSize: '0.875rem', fontWeight: 700, color: '#f8fafc', letterSpacing: '0.04em' }}>
              OPERATOR COMMAND HOTKEYS
            </h3>
          </div>
          <button
            onClick={onClose}
            style={{
              background: 'none',
              border: 'none',
              color: '#64748b',
              cursor: 'pointer',
              padding: '4px',
              display: 'flex',
              alignItems: 'center'
            }}
          >
            <X size={16} />
          </button>
        </div>

        {/* Content */}
        <div style={{ padding: '16px 20px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {shortcuts.map((section) => (
            <div key={section.category}>
              <div
                style={{
                  fontSize: '0.6875rem',
                  fontWeight: 700,
                  textTransform: 'uppercase',
                  letterSpacing: '0.05em',
                  color: '#94a3b8',
                  marginBottom: '8px',
                  borderBottom: '1px solid #161e2e',
                  paddingBottom: '4px'
                }}
              >
                {section.category}
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                {section.items.map((item, idx) => (
                  <div
                    key={idx}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      padding: '4px 0',
                      fontSize: '0.75rem'
                    }}
                  >
                    <span style={{ color: '#cbd5e1' }}>{item.desc}</span>
                    <div style={{ display: 'flex', gap: '4px' }}>
                      {item.keys.map((k) => (
                        <kbd key={k} className="kbd-badge">
                          {k}
                        </kbd>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>

        {/* Footer */}
        <div
          style={{
            padding: '10px 18px',
            backgroundColor: '#090d14',
            borderTop: '1px solid #161e2e',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            fontSize: '0.6875rem',
            color: '#64748b'
          }}
        >
          <span>Press <kbd className="kbd-badge">Esc</kbd> or click outside to dismiss</span>
          <span style={{ fontFamily: 'var(--font-mono, monospace)', color: '#38bdf8' }}>SHIFT-ALPHA-01</span>
        </div>
      </div>
    </div>
  );
};
