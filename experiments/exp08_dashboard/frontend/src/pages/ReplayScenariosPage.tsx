import React, { useState, useEffect, useRef } from 'react';
import {
  Play,
  Pause,
  RotateCcw,
  SkipForward,
  CheckCircle2,
  Sparkles
} from 'lucide-react';
import { StatusBadge } from '../components/StatusBadge';
import { seekDemoPipeline, startScenario } from '../services/api';
import type { StreamStatus, SafetyState, ScenarioStepResult } from '../types';

export interface PhaseConfig {
  id: string;
  title: string;
  frames: string;
  rangeStart: number;
  rangeEnd: number;
  startFrame: number;
  duration: string;
  state: SafetyState;
  desc: string;
  badgeColor: string;
}

export const REPLAY_PHASES: PhaseConfig[] = [
  {
    id: 'NORMAL',
    title: 'Phase 1: Normal Floor Transit',
    frames: 'Frames 0 – 75',
    rangeStart: 0,
    rangeEnd: 75,
    startFrame: 10,
    duration: '~2.5 sec',
    state: 'NORMAL',
    desc: 'Worker enters safe floor corridor. Ground contact point remains within transit boundaries. Zero hazard alarms triggered.',
    badgeColor: '#10b981'
  },
  {
    id: 'WARNING',
    title: 'Phase 2: Warning Buffer Penetration',
    frames: 'Frames 76 – 130',
    rangeStart: 76,
    rangeEnd: 130,
    startFrame: 85,
    duration: '~1.8 sec',
    state: 'WARNING',
    desc: 'Worker veers into yellow buffer zone (+500 mm). Temporal FSM registers 2-frame debouncing hysteresis and triggers WARNING state.',
    badgeColor: '#f59e0b'
  },
  {
    id: 'DANGER',
    title: 'Phase 3: Danger Exclusion Zone Breach',
    frames: 'Frames 131 – 220',
    rangeStart: 131,
    rangeEnd: 220,
    startFrame: 145,
    duration: '~3.0 sec',
    state: 'DANGER',
    desc: 'Worker enters red automated machinery zone. 3-frame hysteresis triggers DANGER breach. Critical safety event is emitted.',
    badgeColor: '#ef4444'
  },
  {
    id: 'RECOVERY',
    title: 'Phase 4: Monotonic Recovery & Safe Egress',
    frames: 'Frames 221 – 540',
    rangeStart: 221,
    rangeEnd: 540,
    startFrame: 235,
    duration: '~3.8 sec',
    state: 'RECOVERY',
    desc: 'Worker exits danger perimeter. System enforces 30-frame (1.0s) monotonic recovery countdown before resetting to NORMAL.',
    badgeColor: '#38bdf8'
  }
];

export function getPhaseForFrame(frame: number): PhaseConfig {
  if (frame <= 75) return REPLAY_PHASES[0];
  if (frame <= 130) return REPLAY_PHASES[1];
  if (frame <= 220) return REPLAY_PHASES[2];
  return REPLAY_PHASES[3];
}

interface ReplayScenariosPageProps {
  streamStatus: StreamStatus | null;
  safetyState: SafetyState;
  onTogglePlay: () => void;
  onRestart: () => void;
  onSeek?: (frame: number) => Promise<any>;
}

export const ReplayScenariosPage: React.FC<ReplayScenariosPageProps> = ({
  streamStatus,
  safetyState,
  onTogglePlay,
  onRestart,
  onSeek
}) => {
  const [isSeeking, setIsSeeking] = useState(false);
  const [localFrame, setLocalFrame] = useState<number | null>(null);
  const [manualLockUntil, setManualLockUntil] = useState<number>(0);
  const [seekError, setSeekError] = useState<string | null>(null);
  const [imgKey, setImgKey] = useState<number>(Date.now());

  // Instant Scenario Lab State
  const [activeScenario, setActiveScenario] = useState<string>('NORMAL_WORKER');
  const [isTriggering, setIsTriggering] = useState<boolean>(false);
  const [scenarioResult, setScenarioResult] = useState<ScenarioStepResult | null>(null);

  // Multi-step Combined Incident State
  const [incidentStep, setIncidentStep] = useState<number>(1);
  const [isPlayingIncident, setIsPlayingIncident] = useState<boolean>(false);
  const incidentTimerRef = useRef<any>(null);

  const seekRequestIdRef = useRef<number>(0);

  const totalFrames = streamStatus?.total_frames ?? 540;
  const currentFrame =
    Date.now() < manualLockUntil && localFrame !== null
      ? localFrame
      : streamStatus?.current_frame_id ?? 0;
  const isRunning = streamStatus?.is_running ?? true;

  const currentPhase = getPhaseForFrame(currentFrame);

  // Trigger instant deterministic scenario
  const handleTriggerScenario = async (scenarioName: string, step?: number) => {
    try {
      setIsTriggering(true);
      setActiveScenario(scenarioName);
      const res = await startScenario(scenarioName, step);
      setScenarioResult(res);
      setImgKey(Date.now());
    } catch (err: any) {
      console.error('Failed to trigger scenario:', err);
    } finally {
      setIsTriggering(false);
    }
  };

  // Multi-step Combined incident autoplay runner
  const handleNextIncidentStep = () => {
    setIncidentStep((prev) => {
      const next = prev >= 4 ? 1 : prev + 1;
      handleTriggerScenario('FULL_CRITICAL_INCIDENT', next);
      return next;
    });
  };

  const handleStepClick = (stepNum: number) => {
    setIncidentStep(stepNum);
    handleTriggerScenario('FULL_CRITICAL_INCIDENT', stepNum);
  };

  const handleTogglePlayIncident = () => {
    if (isPlayingIncident) {
      setIsPlayingIncident(false);
      if (incidentTimerRef.current) clearInterval(incidentTimerRef.current);
    } else {
      setIsPlayingIncident(true);
      handleTriggerScenario('FULL_CRITICAL_INCIDENT', incidentStep);
      incidentTimerRef.current = setInterval(() => {
        setIncidentStep((prev) => {
          if (prev >= 4) {
            setIsPlayingIncident(false);
            clearInterval(incidentTimerRef.current);
            return 4;
          }
          const next = prev + 1;
          handleTriggerScenario('FULL_CRITICAL_INCIDENT', next);
          return next;
        });
      }, 3500);
    }
  };

  const handleResetIncident = () => {
    setIsPlayingIncident(false);
    if (incidentTimerRef.current) clearInterval(incidentTimerRef.current);
    setIncidentStep(1);
    handleTriggerScenario('NORMAL_WORKER');
  };

  useEffect(() => {
    return () => {
      if (incidentTimerRef.current) clearInterval(incidentTimerRef.current);
    };
  }, []);

  const handleSeekCommit = async (frame: number) => {
    const target = Math.max(0, Math.min(totalFrames, Math.round(frame)));
    setLocalFrame(target);
    setManualLockUntil(Date.now() + 1500);
    setIsSeeking(true);
    setSeekError(null);

    const reqId = ++seekRequestIdRef.current;
    try {
      if (onSeek) {
        await onSeek(target);
      } else {
        await seekDemoPipeline(target);
      }
      if (reqId === seekRequestIdRef.current) {
        setImgKey(Date.now());
      }
    } catch (err: any) {
      if (reqId === seekRequestIdRef.current) {
        setSeekError(err.message || 'Seek operation failed');
      }
    } finally {
      if (reqId === seekRequestIdRef.current) {
        setIsSeeking(false);
      }
    }
  };

  return (
    <div style={{ padding: '20px 24px', display: 'flex', flexDirection: 'column', gap: '20px', color: '#f8fafc' }}>
      {/* Header with prominent DEMO MODE Badge */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '14px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <h1 style={{ fontSize: '1.4rem', fontWeight: 800, margin: 0, letterSpacing: '-0.02em' }}>
              SAFETY SCENARIO LAB
            </h1>
            <span
              style={{
                fontSize: '0.6875rem',
                fontWeight: 800,
                padding: '4px 10px',
                borderRadius: '4px',
                backgroundColor: 'rgba(234, 179, 8, 0.2)',
                color: '#fbbf24',
                border: '1px solid rgba(234, 179, 8, 0.4)',
                letterSpacing: '0.08em'
              }}
            >
              DEMO MODE — DETERMINISTIC LAB
            </span>
          </div>
          <p style={{ margin: '4px 0 0 0', color: '#94a3b8', fontSize: '0.8125rem' }}>
            Instantly inject simulated industrial safety incidents across Access, PPE, Spatial Danger,
            Machinery Proximity, and Worker Posture without waiting for video playback.
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '0.75rem', color: '#64748b' }}>Current Active State:</span>
          <StatusBadge state={safetyState} size="md" />
        </div>
      </div>

      {/* ========================================================================= */}
      {/* 1. INSTANT SCENARIO CONTROLS GRID (Prompt 2 Phase 11)                      */}
      {/* ========================================================================= */}
      <div
        style={{
          backgroundColor: '#111827',
          border: '1px solid #1f2937',
          borderRadius: '8px',
          padding: '18px 20px'
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Sparkles size={16} color="#38bdf8" />
            <span style={{ fontSize: '0.8125rem', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.06em', color: '#f8fafc' }}>
              Instant Scenario Controls (Zero Wait Time)
            </span>
          </div>
          <span style={{ fontSize: '0.6875rem', color: '#94a3b8' }}>
            Clicking a scenario immediately shifts entire system state & feeds alerts
          </span>
        </div>

        {/* 12 Scenario Buttons Grid */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
            gap: '10px'
          }}
        >
          {[
            { id: 'NORMAL_WORKER', label: 'NORMAL WORKER', color: '#22c55e', desc: '100% compliant, 0 risk baseline' },
            { id: 'PPE_VIOLATION', label: 'PPE VIOLATION', color: '#f59e0b', desc: 'Missing helmet & gloves (+30)' },
            { id: 'PPE_COMPLIANT', label: 'PPE COMPLIANT', color: '#22c55e', desc: 'Full gear verified, 100%' },
            { id: 'WARNING_ZONE', label: 'WARNING ZONE', color: '#f59e0b', desc: 'Buffer perimeter entry (+35)' },
            { id: 'DANGER_ZONE', label: 'DANGER ZONE', color: '#ef4444', desc: 'Physical exclusion breach (+35)' },
            { id: 'MACHINE_PROXIMITY', label: 'MACHINE PROXIMITY', color: '#f59e0b', desc: 'CNC-01 advisory buffer (+20)' },
            { id: 'MACHINE_EXCLUSION', label: 'MACHINE EXCLUSION', color: '#ef4444', desc: 'CNC-01 spindle breach (+40)' },
            { id: 'WORKER_INACTIVE', label: 'WORKER INACTIVE', color: '#f59e0b', desc: 'Static debounced >30s (+20)' },
            { id: 'POSSIBLE_SLEEP', label: 'POSSIBLE SLEEP', color: '#f59e0b', desc: 'Recumbent rest posture (+25)' },
            { id: 'WORKER_FALL', label: 'WORKER FALL', color: '#ef4444', desc: 'PERSON_DOWN critical (+50)' },
            { id: 'ACCESS_DENIED', label: 'ACCESS DENIED', color: '#ef4444', desc: 'Unregistered badge / PPE fail' },
            { id: 'FULL_CRITICAL_INCIDENT', label: 'FULL CRITICAL INCIDENT', color: '#dc2626', desc: '4-step multi-domain incident' }
          ].map((item) => {
            const isSelected = activeScenario === item.id;
            return (
              <button
                key={item.id}
                onClick={() => handleTriggerScenario(item.id)}
                disabled={isTriggering}
                style={{
                  backgroundColor: isSelected ? 'rgba(37, 99, 235, 0.25)' : '#0f172a',
                  border: `1px solid ${isSelected ? item.color : '#334155'}`,
                  borderRadius: '6px',
                  padding: '10px 12px',
                  textAlign: 'left',
                  cursor: isTriggering ? 'wait' : 'pointer',
                  transition: 'all 0.15s ease',
                  position: 'relative'
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <span
                    style={{
                      fontSize: '0.75rem',
                      fontWeight: 800,
                      color: isSelected ? item.color : '#f8fafc',
                      letterSpacing: '0.02em'
                    }}
                  >
                    [ {item.label} ]
                  </span>
                  {isSelected && <CheckCircle2 size={13} color={item.color} />}
                </div>
                <div style={{ fontSize: '0.625rem', color: '#94a3b8', marginTop: '4px' }}>
                  {item.desc}
                </div>
              </button>
            );
          })}
        </div>

        {/* Real-time Execution Banner */}
        {scenarioResult && (
          <div
            style={{
              marginTop: '14px',
              padding: '10px 14px',
              borderRadius: '6px',
              backgroundColor: '#0c1018',
              border: '1px solid #1e293b',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              fontSize: '0.75rem'
            }}
          >
            <div>
              <span style={{ color: '#38bdf8', fontWeight: 700 }}>
                {scenarioResult.scenario}:
              </span>{' '}
              <span style={{ color: '#cbd5e1' }}>{scenarioResult.message}</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', fontSize: '0.6875rem', color: '#64748b' }}>
              <span>Latency: {scenarioResult.execution_time_ms ? `${scenarioResult.execution_time_ms.toFixed(1)} ms` : '< 1 ms'}</span>
              <span>•</span>
              <span>Emitted: {scenarioResult.emitted_events?.length ?? 1} events</span>
            </div>
          </div>
        )}
      </div>

      {/* ========================================================================= */}
      {/* 2. MULTI-STEP COMBINED DEMONSTRATION RUNNER (Prompt 2 Phase 12)            */}
      {/* ========================================================================= */}
      <div
        style={{
          backgroundColor: '#111827',
          border: '1px solid #1f2937',
          borderRadius: '8px',
          padding: '18px 20px'
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px', flexWrap: 'wrap', gap: '10px' }}>
          <div>
            <div style={{ fontSize: '0.8125rem', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.06em', color: '#f8fafc' }}>
              Full Safety Incident (Multi-Scenario Pipeline Demo)
            </div>
            <div style={{ fontSize: '0.6875rem', color: '#94a3b8', marginTop: '2px' }}>
              Demonstrate the complete safety lifecycle in 1–2 minutes: Shift Entry &rarr; PPE Violation &rarr; Warning Zone &rarr; Machine Breach &rarr; Worker Fall.
            </div>
          </div>

          {/* Autoplay Controls */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <button
              onClick={handleTogglePlayIncident}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                backgroundColor: isPlayingIncident ? '#d97706' : '#2563eb',
                border: 'none',
                color: '#ffffff',
                padding: '6px 12px',
                borderRadius: '5px',
                fontSize: '0.75rem',
                fontWeight: 700,
                cursor: 'pointer'
              }}
            >
              {isPlayingIncident ? <Pause size={13} /> : <Play size={13} />}
              {isPlayingIncident ? 'PAUSE' : 'PLAY AUTOPLAY'}
            </button>

            <button
              onClick={handleNextIncidentStep}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                backgroundColor: '#1e293b',
                border: '1px solid #334155',
                color: '#cbd5e1',
                padding: '6px 12px',
                borderRadius: '5px',
                fontSize: '0.75rem',
                fontWeight: 700,
                cursor: 'pointer'
              }}
            >
              <SkipForward size={13} />
              NEXT EVENT
            </button>

            <button
              onClick={handleResetIncident}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                backgroundColor: '#1e293b',
                border: '1px solid #334155',
                color: '#94a3b8',
                padding: '6px 10px',
                borderRadius: '5px',
                fontSize: '0.75rem',
                fontWeight: 600,
                cursor: 'pointer'
              }}
            >
              <RotateCcw size={13} />
              RESET
            </button>
          </div>
        </div>

        {/* 4 Discrete Step Cards */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '10px' }}>
          {[
            {
              step: 1,
              title: 'STEP 1: ENTRY & PPE CHECK',
              desc: 'Worker enters Bay 01. Verified identity, but missing helmet violation emitted (+20 risk).',
              score: 20,
              level: 'LOW'
            },
            {
              step: 2,
              title: 'STEP 2: WARNING ZONE BUFFER',
              desc: 'Worker encroaches into 1.2m yellow perimeter buffer (+15 risk -> 35 total).',
              score: 35,
              level: 'MEDIUM'
            },
            {
              step: 3,
              title: 'STEP 3: MACHINE EXCLUSION',
              desc: 'Worker breaches CNC-01 spindle exclusion perimeter at 1.4m clearance (+40 risk -> 75 total).',
              score: 75,
              level: 'HIGH'
            },
            {
              step: 4,
              title: 'STEP 4: WORKER FALL & SIREN',
              desc: 'Worker falls (aspect ratio 2.5). Emergency siren dispatched & risk capped at 100.',
              score: 100,
              level: 'CRITICAL'
            }
          ].map((item) => {
            const isCurrent = incidentStep === item.step;
            return (
              <div
                key={item.step}
                onClick={() => handleStepClick(item.step)}
                style={{
                  backgroundColor: isCurrent ? 'rgba(37, 99, 235, 0.15)' : '#0f172a',
                  border: `1px solid ${isCurrent ? '#38bdf8' : '#1e293b'}`,
                  borderRadius: '6px',
                  padding: '12px',
                  cursor: 'pointer',
                  transition: 'all 0.15s ease'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: '0.6875rem', fontWeight: 800, color: isCurrent ? '#38bdf8' : '#94a3b8' }}>
                    {item.title}
                  </span>
                  <span
                    style={{
                      fontSize: '0.625rem',
                      fontWeight: 700,
                      padding: '2px 5px',
                      borderRadius: '3px',
                      backgroundColor: item.score >= 75 ? 'rgba(239, 68, 68, 0.2)' : 'rgba(234, 179, 8, 0.2)',
                      color: item.score >= 75 ? '#f87171' : '#fbbf24'
                    }}
                  >
                    Risk: {item.score}
                  </span>
                </div>
                <div style={{ fontSize: '0.6875rem', color: '#cbd5e1', marginTop: '6px', lineHeight: 1.3 }}>
                  {item.desc}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* ========================================================================= */}
      {/* 3. CALIBRATED VIDEO PLAYER & TIMELINE REPLAY (Preserved Functionality)     */}
      {/* ========================================================================= */}
      <div
        style={{
          backgroundColor: '#111827',
          border: '1px solid #1f2937',
          borderRadius: '8px',
          padding: '18px 20px'
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
          <div>
            <div style={{ fontSize: '0.8125rem', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.06em', color: '#f8fafc' }}>
              Calibrated Floor Video Stream & Replay Scrubber
            </div>
            <div style={{ fontSize: '0.6875rem', color: '#94a3b8' }}>
              Preserved continuous video pipeline with CNC-01 exclusion region overlay & 4-phase transition timeline.
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <button
              onClick={onTogglePlay}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '5px',
                backgroundColor: isRunning ? '#1e293b' : '#2563eb',
                border: '1px solid #334155',
                color: '#ffffff',
                padding: '6px 12px',
                borderRadius: '5px',
                fontSize: '0.75rem',
                fontWeight: 600,
                cursor: 'pointer'
              }}
            >
              {isRunning ? <Pause size={13} /> : <Play size={13} />}
              {isRunning ? 'Pause Video' : 'Resume Video'}
            </button>
            <button
              onClick={onRestart}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '5px',
                backgroundColor: '#1e293b',
                border: '1px solid #334155',
                color: '#94a3b8',
                padding: '6px 10px',
                borderRadius: '5px',
                fontSize: '0.75rem',
                cursor: 'pointer'
              }}
            >
              <RotateCcw size={13} />
              Rewind
            </button>
          </div>
        </div>

        {/* Video Frame */}
        <div
          style={{
            height: '360px',
            backgroundColor: '#090b10',
            borderRadius: '6px',
            overflow: 'hidden',
            border: '1px solid #1e293b',
            position: 'relative'
          }}
        >
          <img
            key={imgKey}
            src={`/api/stream/mjpeg?t=${imgKey}`}
            alt="Safety Scenario CCTV Stream"
            style={{ width: '100%', height: '100%', objectFit: 'contain' }}
            onError={(e) => {
              (e.currentTarget as HTMLElement).style.display = 'none';
            }}
          />
        </div>

        {/* Scrubber Bar */}
        <div style={{ marginTop: '14px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.6875rem', color: '#94a3b8', marginBottom: '6px' }}>
            <span>Frame: {currentFrame} / {totalFrames}</span>
            <span>Phase: {currentPhase.title}</span>
            <span>Time: {((currentFrame / 30)).toFixed(1)}s</span>
          </div>
          <input
            type="range"
            min={0}
            max={totalFrames}
            value={currentFrame}
            onChange={(e) => handleSeekCommit(Number(e.target.value))}
            style={{ width: '100%', accentColor: '#38bdf8', cursor: isSeeking ? 'wait' : 'pointer' }}
          />
          {seekError && (
            <div style={{ color: '#ef4444', fontSize: '0.6875rem', marginTop: '4px' }}>
              Seek warning: {seekError}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
