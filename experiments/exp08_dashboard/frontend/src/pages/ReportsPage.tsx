import React from 'react';
import {
  Printer,
  Award,
  CheckCircle2,
  Info
} from 'lucide-react';

export const ReportsPage: React.FC = () => {
  const criteria = [
    { id: 'AC-01', title: 'Normal Transit Clean vs Noisy', metric: 'State Accuracy >= 95%', observed: '100.0%', status: 'PASS' },
    { id: 'AC-02', title: 'Acute Breach Time-to-Alert', metric: 'TTA <= 500 ms', observed: '96.7 ms', status: 'PASS' },
    { id: 'AC-03', title: 'Shadow Rejection', metric: '0 False Danger Breaches', observed: '0 False Alarms', status: 'PASS' },
    { id: 'AC-04', title: 'Recovery Within 1.0 Second', metric: 'T_rec <= 1000 ms', observed: '1.0 s (30 frames)', status: 'PASS' },
    { id: 'AC-05', title: 'Temporary Occlusion Continuity', metric: 'Track ID Preserved', observed: 'Track #1 Maintained', status: 'PASS' },
    { id: 'AC-06', title: 'Camera Watchdog Timeout', metric: 'Timeout <= 1000 ms', observed: '66.7 ms Heartbeat', status: 'PASS' },
    { id: 'AC-07', title: 'Sustained Framerate (Profile-Aware)', metric: 'Profile Benchmark', observed: '8.1 FPS (Battery/DC)', status: 'PASS' },
    { id: 'AC-08', title: 'Bounded Queue Depth', metric: 'Queue <= 30 frames', observed: 'Peak 1/30 (0 Drops)', status: 'PASS' },
    { id: 'AC-09', title: 'Invalid Calibration Rejection', metric: 'det(H) < 1e-6 Rejection', observed: 'Zero-Determinant Blocked', status: 'PASS' },
    { id: 'AC-10', title: 'Face Privacy Compliance', metric: 'Upper 25% Obfuscation', observed: '100% Facial Blur', status: 'PASS' }
  ];

  const experimentsTimeline = [
    { exp: 'Exp 01', name: 'Detector Benchmark', focus: 'YOLOv8n CPU throughput & warmup methodology', status: 'VALIDATED' },
    { exp: 'Exp 02', name: 'Tracker Stability', focus: 'ByteTrack Kalman continuity across occlusions', status: 'VALIDATED' },
    { exp: 'Exp 03', name: 'Planar Homography', focus: 'Floor coordinate calibration & geometric bounds', status: 'VALIDATED' },
    { exp: 'Exp 04', name: 'Safety Zone Geometry', focus: 'Polygon containment & Ray-casting accuracy', status: 'VALIDATED' },
    { exp: 'Exp 05', name: 'Temporal FSM', focus: 'Hysteresis debounce & 30-frame recovery', status: 'VALIDATED' },
    { exp: 'Exp 06', name: 'Watchdog & Queue', focus: 'Heartbeat timeout & bounded drop-oldest ring', status: 'VALIDATED' },
    { exp: 'Exp 07', name: 'Event Engine & DB', focus: 'SQLite WAL audit logging & deduplication', status: 'VALIDATED' },
    { exp: 'Exp 08', name: 'FastAPI Dashboard', focus: 'Real-time WebSocket streaming & operator actions', status: 'VALIDATED' },
    { exp: 'Exp 09', name: 'Offline Evaluation & Privacy', focus: 'Ground-truth evaluation & 100% face obfuscation', status: 'VALIDATED' }
  ];

  const handlePrint = () => {
    window.print();
  };

  return (
    <div style={{ padding: '20px 24px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Header & Export Options */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          backgroundColor: '#0c1018',
          border: '1px solid #161e2e',
          borderRadius: '6px',
          padding: '16px 20px'
        }}
      >
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Award size={20} color="#10b981" />
            <h2 style={{ fontSize: '1.125rem', fontWeight: 600, color: '#f8fafc' }}>
              WorkSafe AI — Project Validation Results
            </h2>
          </div>
          <p style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '4px' }}>
            Documented engineering verification across Experiments 01–09, full 146-test regression suite, and ISO 13849-1 supervisory boundaries.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '10px' }}>
          <button
            onClick={handlePrint}
            style={{
              padding: '6px 14px',
              borderRadius: '4px',
              backgroundColor: '#070a10',
              border: '1px solid #1c2638',
              color: '#f8fafc',
              fontSize: '0.75rem',
              fontWeight: 500,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px'
            }}
          >
            <Printer size={14} />
            <span>Print Report</span>
          </button>
        </div>
      </div>

      {/* Executive Summary Card */}
      <div
        style={{
          backgroundColor: '#0c1018',
          border: '1px solid #161e2e',
          borderLeft: '4px solid #38bdf8',
          borderRadius: '6px',
          padding: '16px 20px',
          display: 'flex',
          flexDirection: 'column',
          gap: '8px'
        }}
      >
        <div style={{ fontSize: '0.8125rem', fontWeight: 700, color: '#f8fafc', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
          EXECUTIVE SUMMARY & OPERATIONAL SCOPE
        </div>
        <p style={{ fontSize: '0.8125rem', color: '#cbd5e1', lineHeight: 1.5 }}>
          WorkSafe AI is an enterprise supervisory vision system for industrial safety monitoring, zone compliance auditing, and operator situational awareness. The system executes a deterministic 11-stage pipeline (YOLOv8, ByteTrack, Planar Homography, Ray-Casting Polygon Classification, and Temporal FSM Debouncing) to detect unauthorized buffer intrusions and acute exclusion breaches in real time.
        </p>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px', marginTop: '4px', fontSize: '0.75rem' }}>
          <div style={{ backgroundColor: '#070a10', padding: '8px 12px', borderRadius: '4px', border: '1px solid #161e2e' }}>
            <span style={{ color: '#64748b' }}>Verification Verdict: </span>
            <strong style={{ color: '#34d399' }}>10/10 Objectives Passed</strong>
          </div>
          <div style={{ backgroundColor: '#070a10', padding: '8px 12px', borderRadius: '4px', border: '1px solid #161e2e' }}>
            <span style={{ color: '#64748b' }}>Privacy Verification: </span>
            <strong style={{ color: '#38bdf8' }}>100% Zero-Biometrics Obfuscation</strong>
          </div>
          <div style={{ backgroundColor: '#070a10', padding: '8px 12px', borderRadius: '4px', border: '1px solid #161e2e' }}>
            <span style={{ color: '#64748b' }}>Regulatory Classification: </span>
            <strong style={{ color: '#fbbf24' }}>Supervisory Only (Non-SIL)</strong>
          </div>
        </div>
      </div>

      {/* ========================================================================= */}
      {/* EXECUTIVE VISUALIZATION: SAFETY PERFORMANCE OVERVIEW (AUDIT PERIOD)       */}
      {/* ========================================================================= */}
      <section
        aria-label="Safety Performance Overview"
        style={{
          backgroundColor: '#0c1018',
          border: '1px solid #161e2e',
          borderRadius: '6px',
          padding: '16px 20px',
          display: 'flex',
          flexDirection: 'column',
          gap: '14px'
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <div style={{ fontSize: '0.8125rem', fontWeight: 700, color: '#f8fafc', letterSpacing: '0.04em' }}>
              SAFETY PERFORMANCE OVERVIEW (EVALUATION AUDIT PERIOD)
            </div>
            <p style={{ fontSize: '0.6875rem', color: '#64748b', marginTop: '2px' }}>
              Supervisory performance metrics across the complete reference factory safety scenario.
            </p>
          </div>
          <span style={{ fontSize: '0.625rem', fontFamily: 'var(--font-mono, monospace)', color: '#38bdf8' }}>
            Reference: industrial_factory_demo.mp4
          </span>
        </div>

        {/* 6 Executive KPI Badges */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(6, 1fr)', gap: '10px' }}>
          <div style={{ backgroundColor: '#07090f', padding: '10px 12px', borderRadius: '4px', border: '1px solid #161e2e' }}>
            <div style={{ fontSize: '0.5625rem', color: '#64748b', textTransform: 'uppercase' }}>Monitored Time</div>
            <div style={{ fontFamily: 'var(--font-mono, monospace)', fontSize: '1.125rem', fontWeight: 700, color: '#f8fafc', marginTop: '2px' }}>
              18.0 s
            </div>
            <div style={{ fontSize: '0.5625rem', color: '#94a3b8' }}>540 Replay Frames</div>
          </div>

          <div style={{ backgroundColor: '#07090f', padding: '10px 12px', borderRadius: '4px', border: '1px solid #161e2e' }}>
            <div style={{ fontSize: '0.5625rem', color: '#64748b', textTransform: 'uppercase' }}>Warning Events</div>
            <div style={{ fontFamily: 'var(--font-mono, monospace)', fontSize: '1.125rem', fontWeight: 700, color: '#fbbf24', marginTop: '2px' }}>
              1 Event
            </div>
            <div style={{ fontSize: '0.5625rem', color: '#94a3b8' }}>Buffer Penetration</div>
          </div>

          <div style={{ backgroundColor: '#07090f', padding: '10px 12px', borderRadius: '4px', border: '1px solid #161e2e' }}>
            <div style={{ fontSize: '0.5625rem', color: '#64748b', textTransform: 'uppercase' }}>Danger Breaches</div>
            <div style={{ fontFamily: 'var(--font-mono, monospace)', fontSize: '1.125rem', fontWeight: 700, color: '#f87171', marginTop: '2px' }}>
              1 Acute
            </div>
            <div style={{ fontSize: '0.5625rem', color: '#94a3b8' }}>Exclusion Zone</div>
          </div>

          <div style={{ backgroundColor: '#07090f', padding: '10px 12px', borderRadius: '4px', border: '1px solid #161e2e' }}>
            <div style={{ fontSize: '0.5625rem', color: '#64748b', textTransform: 'uppercase' }}>Response Latency</div>
            <div style={{ fontFamily: 'var(--font-mono, monospace)', fontSize: '1.125rem', fontWeight: 700, color: '#34d399', marginTop: '2px' }}>
              96.7 ms
            </div>
            <div style={{ fontSize: '0.5625rem', color: '#34d399' }}>SLA &lt;= 500ms (PASS)</div>
          </div>

          <div style={{ backgroundColor: '#07090f', padding: '10px 12px', borderRadius: '4px', border: '1px solid #161e2e' }}>
            <div style={{ fontSize: '0.5625rem', color: '#64748b', textTransform: 'uppercase' }}>Max Hazard Exposure</div>
            <div style={{ fontFamily: 'var(--font-mono, monospace)', fontSize: '1.125rem', fontWeight: 700, color: '#fbbf24', marginTop: '2px' }}>
              3.0 s
            </div>
            <div style={{ fontSize: '0.5625rem', color: '#94a3b8' }}>Machinery Cell Entry</div>
          </div>

          <div style={{ backgroundColor: '#07090f', padding: '10px 12px', borderRadius: '4px', border: '1px solid #161e2e' }}>
            <div style={{ fontSize: '0.5625rem', color: '#64748b', textTransform: 'uppercase' }}>Recovery Reset</div>
            <div style={{ fontFamily: 'var(--font-mono, monospace)', fontSize: '1.125rem', fontWeight: 700, color: '#38bdf8', marginTop: '2px' }}>
              1.0 s
            </div>
            <div style={{ fontSize: '0.5625rem', color: '#38bdf8' }}>30-Frame Monotonic</div>
          </div>
        </div>

        {/* Phase Timeline Band */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
          <div style={{ height: '16px', backgroundColor: '#07090f', borderRadius: '3px', overflow: 'hidden', display: 'flex', border: '1px solid #161e2e' }}>
            <div title="Phase 1: Normal Floor Transit (13.9%)" style={{ width: '13.9%', backgroundColor: 'rgba(16, 185, 129, 0.4)', borderRight: '1px solid #059669', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.5rem', color: '#34d399', fontWeight: 700 }}>
              NORMAL
            </div>
            <div title="Phase 2: Warning Buffer Entry (10.2%)" style={{ width: '10.2%', backgroundColor: 'rgba(245, 158, 11, 0.4)', borderRight: '1px solid #d97706', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.5rem', color: '#fbbf24', fontWeight: 700 }}>
              WARN
            </div>
            <div title="Phase 3: Danger Zone Breach (16.7%)" style={{ width: '16.7%', backgroundColor: 'rgba(239, 68, 68, 0.5)', borderRight: '1px solid #dc2626', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.5rem', color: '#f87171', fontWeight: 700 }}>
              DANGER
            </div>
            <div title="Phase 4: Monotonic Egress & Clear (59.2%)" style={{ width: '59.2%', backgroundColor: 'rgba(56, 189, 248, 0.3)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.5rem', color: '#38bdf8', fontWeight: 700 }}>
              RECOVERY & SAFE EGRESS
            </div>
          </div>
        </div>
      </section>

      {/* Verified Metrics Scorecard (All Required Metrics) */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(4, 1fr)',
          gap: '12px'
        }}
      >
        <div style={{ backgroundColor: '#0c1018', border: '1px solid #161e2e', borderTop: '3px solid #10b981', borderRadius: '6px', padding: '14px' }}>
          <div style={{ fontSize: '0.625rem', color: '#64748b', textTransform: 'uppercase' }}>REGRESSION SUITE</div>
          <div style={{ fontFamily: 'var(--font-mono, monospace)', fontSize: '1.5rem', fontWeight: 700, color: '#34d399', marginTop: '4px' }}>
            146 / 146
          </div>
          <div style={{ fontSize: '0.6875rem', color: '#94a3b8', marginTop: '2px' }}>100.0% Pass Rate</div>
        </div>

        <div style={{ backgroundColor: '#0c1018', border: '1px solid #161e2e', borderTop: '3px solid #10b981', borderRadius: '6px', padding: '14px' }}>
          <div style={{ fontSize: '0.625rem', color: '#64748b', textTransform: 'uppercase' }}>ACCEPTANCE CRITERIA</div>
          <div style={{ fontFamily: 'var(--font-mono, monospace)', fontSize: '1.5rem', fontWeight: 700, color: '#34d399', marginTop: '4px' }}>
            10 / 10
          </div>
          <div style={{ fontSize: '0.6875rem', color: '#94a3b8', marginTop: '2px' }}>All Objectives Verified</div>
        </div>

        <div style={{ backgroundColor: '#0c1018', border: '1px solid #161e2e', borderTop: '3px solid #38bdf8', borderRadius: '6px', padding: '14px' }}>
          <div style={{ fontSize: '0.625rem', color: '#64748b', textTransform: 'uppercase' }}>PRECISION / RECALL / F1</div>
          <div style={{ fontFamily: 'var(--font-mono, monospace)', fontSize: '1.5rem', fontWeight: 700, color: '#38bdf8', marginTop: '4px' }}>
            1.000 / 1.000
          </div>
          <div style={{ fontSize: '0.6875rem', color: '#94a3b8', marginTop: '2px' }}>Zero False Alarms / Zero Misses</div>
        </div>

        <div style={{ backgroundColor: '#0c1018', border: '1px solid #161e2e', borderTop: '3px solid #38bdf8', borderRadius: '6px', padding: '14px' }}>
          <div style={{ fontSize: '0.625rem', color: '#64748b', textTransform: 'uppercase' }}>TIME-TO-ALERT (TTA)</div>
          <div style={{ fontFamily: 'var(--font-mono, monospace)', fontSize: '1.5rem', fontWeight: 700, color: '#38bdf8', marginTop: '4px' }}>
            96.7 ms
          </div>
          <div style={{ fontSize: '0.6875rem', color: '#94a3b8', marginTop: '2px' }}>Threshold: &lt;= 500 ms</div>
        </div>

        <div style={{ backgroundColor: '#0c1018', border: '1px solid #161e2e', borderTop: '3px solid #10b981', borderRadius: '6px', padding: '14px' }}>
          <div style={{ fontSize: '0.625rem', color: '#64748b', textTransform: 'uppercase' }}>WATCHDOG TIMEOUT</div>
          <div style={{ fontFamily: 'var(--font-mono, monospace)', fontSize: '1.5rem', fontWeight: 700, color: '#34d399', marginTop: '4px' }}>
            1.0 s
          </div>
          <div style={{ fontSize: '0.6875rem', color: '#94a3b8', marginTop: '2px' }}>66.7 ms Measured Heartbeat</div>
        </div>

        <div style={{ backgroundColor: '#0c1018', border: '1px solid #161e2e', borderTop: '3px solid #38bdf8', borderRadius: '6px', padding: '14px' }}>
          <div style={{ fontSize: '0.625rem', color: '#64748b', textTransform: 'uppercase' }}>QUEUE DEPTH LIMIT</div>
          <div style={{ fontFamily: 'var(--font-mono, monospace)', fontSize: '1.5rem', fontWeight: 700, color: '#38bdf8', marginTop: '4px' }}>
            30 Frames
          </div>
          <div style={{ fontSize: '0.6875rem', color: '#94a3b8', marginTop: '2px' }}>Bounded Drop-Oldest Buffer</div>
        </div>

        <div style={{ backgroundColor: '#0c1018', border: '1px solid #161e2e', borderTop: '3px solid #a855f7', borderRadius: '6px', padding: '14px' }}>
          <div style={{ fontSize: '0.625rem', color: '#64748b', textTransform: 'uppercase' }}>PRIVACY COMPLIANCE</div>
          <div style={{ fontFamily: 'var(--font-mono, monospace)', fontSize: '1.5rem', fontWeight: 700, color: '#c084fc', marginTop: '4px' }}>
            100%
          </div>
          <div style={{ fontSize: '0.6875rem', color: '#94a3b8', marginTop: '2px' }}>Zero Biometrics / Face Blur</div>
        </div>

        <div style={{ backgroundColor: '#0c1018', border: '1px solid #161e2e', borderTop: '3px solid #10b981', borderRadius: '6px', padding: '14px' }}>
          <div style={{ fontSize: '0.625rem', color: '#64748b', textTransform: 'uppercase' }}>RECOVERY LATENCY</div>
          <div style={{ fontFamily: 'var(--font-mono, monospace)', fontSize: '1.5rem', fontWeight: 700, color: '#34d399', marginTop: '4px' }}>
            1.000 s
          </div>
          <div style={{ fontSize: '0.6875rem', color: '#94a3b8', marginTop: '2px' }}>30 Consecutive Clean Frames</div>
        </div>
      </div>

      {/* 10 Acceptance Criteria Formal Matrix */}
      <div
        style={{
          backgroundColor: '#0c1018',
          border: '1px solid #161e2e',
          borderRadius: '6px',
          overflow: 'hidden'
        }}
      >
        <div
          style={{
            padding: '12px 18px',
            borderBottom: '1px solid #161e2e',
            backgroundColor: '#0f1420',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between'
          }}
        >
          <span style={{ fontSize: '0.8125rem', fontWeight: 700, color: '#f8fafc', letterSpacing: '0.04em' }}>
            ACCEPTANCE CRITERIA VERIFICATION MATRIX (AC-01 — AC-10)
          </span>
          <span style={{ fontSize: '0.625rem', color: '#10b981', fontWeight: 700 }}>
            ALL 10 VERIFIED
          </span>
        </div>

        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.75rem' }}>
            <thead>
              <tr style={{ backgroundColor: '#070a10', borderBottom: '1px solid #161e2e', color: '#64748b', fontWeight: 700, textTransform: 'uppercase', fontSize: '0.625rem' }}>
                <th style={{ padding: '10px 14px' }}>ID</th>
                <th style={{ padding: '10px 14px' }}>Criterion Title</th>
                <th style={{ padding: '10px 14px' }}>Target Specification</th>
                <th style={{ padding: '10px 14px' }}>Observed Result</th>
                <th style={{ padding: '10px 14px' }}>Status</th>
              </tr>
            </thead>
            <tbody>
              {criteria.map((c) => (
                <tr key={c.id} style={{ borderBottom: '1px solid #141a27' }}>
                  <td style={{ padding: '10px 14px', fontFamily: 'var(--font-mono, monospace)', color: '#38bdf8', fontWeight: 700 }}>
                    {c.id}
                  </td>
                  <td style={{ padding: '10px 14px', fontWeight: 600, color: '#f8fafc' }}>
                    {c.title}
                  </td>
                  <td style={{ padding: '10px 14px', color: '#94a3b8' }}>
                    {c.metric}
                  </td>
                  <td style={{ padding: '10px 14px', fontFamily: 'var(--font-mono, monospace)', color: '#34d399', fontWeight: 600 }}>
                    {c.observed}
                  </td>
                  <td style={{ padding: '10px 14px' }}>
                    <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', fontSize: '0.625rem', padding: '2px 6px', borderRadius: '3px', backgroundColor: 'rgba(16, 185, 129, 0.15)', color: '#34d399', fontWeight: 700 }}>
                      <CheckCircle2 size={11} />
                      <span>{c.status}</span>
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Experiment 01–09 Implementation Timeline */}
      <div
        style={{
          backgroundColor: '#0c1018',
          border: '1px solid #161e2e',
          borderRadius: '6px',
          overflow: 'hidden'
        }}
      >
        <div
          style={{
            padding: '12px 18px',
            borderBottom: '1px solid #161e2e',
            backgroundColor: '#0f1420'
          }}
        >
          <span style={{ fontSize: '0.8125rem', fontWeight: 700, color: '#f8fafc', letterSpacing: '0.04em' }}>
            EXPERIMENT 01–09 VALIDATION TIMELINE
          </span>
        </div>

        <div style={{ padding: '14px 18px', display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px' }}>
          {experimentsTimeline.map((item) => (
            <div
              key={item.exp}
              style={{
                backgroundColor: '#070a10',
                border: '1px solid #161e2e',
                borderRadius: '4px',
                padding: '10px 12px'
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontFamily: 'var(--font-mono, monospace)', color: '#38bdf8', fontWeight: 700, fontSize: '0.75rem' }}>
                  {item.exp}
                </span>
                <span style={{ fontSize: '0.625rem', padding: '1px 5px', borderRadius: '3px', backgroundColor: 'rgba(16, 185, 129, 0.15)', color: '#34d399', fontWeight: 700 }}>
                  {item.status}
                </span>
              </div>
              <div style={{ fontSize: '0.75rem', fontWeight: 600, color: '#f8fafc', marginTop: '4px' }}>
                {item.name}
              </div>
              <div style={{ fontSize: '0.6875rem', color: '#64748b', marginTop: '2px' }}>
                {item.focus}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Hardware Profile Benchmark & Known Limitations */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gap: '16px'
        }}
      >
        {/* Hardware Benchmark Comparison */}
        <div style={{ backgroundColor: '#0c1018', border: '1px solid #161e2e', borderRadius: '6px', padding: '16px 18px' }}>
          <div style={{ fontSize: '0.8125rem', fontWeight: 700, color: '#f8fafc', marginBottom: '12px' }}>
            HARDWARE BENCHMARK COMPARISON
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '0.75rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px', backgroundColor: '#070a10', borderRadius: '4px' }}>
              <span style={{ color: '#cbd5e1' }}>Battery / DC Power Profile</span>
              <strong style={{ fontFamily: 'var(--font-mono, monospace)', color: '#38bdf8' }}>8.1 FPS | 122.7 ms Latency</strong>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px', backgroundColor: '#070a10', borderRadius: '4px' }}>
              <span style={{ color: '#cbd5e1' }}>AC Mains High-Performance Profile</span>
              <strong style={{ fontFamily: 'var(--font-mono, monospace)', color: '#34d399' }}>18.4 FPS | 54.3 ms Latency</strong>
            </div>
            <div style={{ fontSize: '0.6875rem', color: '#64748b', marginTop: '4px' }}>
              * Both hardware profiles sustain Time-to-Alert (TTA) under the 500 ms safety requirement.
            </div>
          </div>
        </div>

        {/* Known Technical Limitations */}
        <div style={{ backgroundColor: '#0c1018', border: '1px solid #161e2e', borderRadius: '6px', padding: '16px 18px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.8125rem', fontWeight: 700, color: '#f8fafc', marginBottom: '12px' }}>
            <Info size={14} color="#38bdf8" />
            <span>OPERATING ASSUMPTIONS & BOUNDARIES</span>
          </div>
          <ul style={{ paddingLeft: '18px', display: 'flex', flexDirection: 'column', gap: '6px', fontSize: '0.6875rem', color: '#94a3b8' }}>
            <li>Planar Homography assumes ground plane $Z=0$ mm across the calibrated floor corridor.</li>
            <li>Zero-Biometrics Policy strictly prohibits facial feature extraction or identity persistence.</li>
            <li>Supervisory AI only: does not substitute for certified Category 4 emergency hardware e-stops.</li>
            <li>Lossy Queue: Drops oldest frame if ingestion exceeds processing to guarantee real-time latency.</li>
          </ul>
        </div>
      </div>
    </div>
  );
};
