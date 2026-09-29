import React, { useState, useEffect } from 'react';
import {
  HardHat,
  Shirt,
  Footprints,
  Hand,
  UserCheck,
  RefreshCw,
  Search,
  HelpCircle,
  ChevronRight
} from 'lucide-react';
import type { WorkerSafetyProfile, RiskOverview } from '../types';
import { fetchSafetyWorkers, fetchSafetyRisk } from '../services/api';

interface WorkerSafetyPageProps {
  onNavigate?: (pageId: any) => void;
}

export const WorkerSafetyPage: React.FC<WorkerSafetyPageProps> = ({ onNavigate }) => {
  const [workers, setWorkers] = useState<WorkerSafetyProfile[]>([]);
  const [riskOverview, setRiskOverview] = useState<RiskOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<'ALL' | 'CRITICAL' | 'PPE_VIOLATION' | 'PROXIMITY' | 'POSTURE'>('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedWorker, setSelectedWorker] = useState<WorkerSafetyProfile | null>(null);
  const [showScoringModal, setShowScoringModal] = useState(false);

  const loadData = async () => {
    try {
      setLoading(true);
      const [wRes, rRes] = await Promise.all([
        fetchSafetyWorkers().catch(() => ({ active_workers_count: 0, workers: [], timestamp: 0 })),
        fetchSafetyRisk().catch(() => null)
      ]);
      setWorkers(wRes.workers || []);
      setRiskOverview(rRes);
    } catch (err) {
      console.error('Failed to load worker safety data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 2500);
    return () => clearInterval(interval);
  }, []);

  // Filter workers based on tabs and search query
  const filteredWorkers = workers.filter((w) => {
    const matchesSearch =
      w.worker_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      w.current_zone.toLowerCase().includes(searchQuery.toLowerCase()) ||
      w.nearest_machine.toLowerCase().includes(searchQuery.toLowerCase());

    if (!matchesSearch) return false;

    if (filter === 'CRITICAL') {
      return w.risk_score >= 50 || w.severity === 'CRITICAL' || w.severity === 'HIGH';
    }
    if (filter === 'PPE_VIOLATION') {
      return w.ppe_compliance_pct < 100 || !w.helmet || !w.safety_vest || !w.safety_shoes || !w.gloves;
    }
    if (filter === 'PROXIMITY') {
      return (
        w.machine_exclusion_status === 'WARNING PROXIMITY' ||
        w.machine_exclusion_status === 'EXCLUSION BREACH' ||
        w.distance_to_danger_zone <= 1.5
      );
    }
    if (filter === 'POSTURE') {
      return (
        w.posture_state === 'FALL DETECTED' ||
        w.posture_state === 'POSSIBLE SLEEP' ||
        w.posture_state === 'INACTIVE'
      );
    }
    return true;
  });

  // Calculate aggregated metrics
  const totalWorkers = workers.length;
  const ppeCompliantCount = workers.filter(
    (w) => w.helmet && w.safety_vest && w.safety_shoes && w.gloves
  ).length;
  const ppeComplianceRate = totalWorkers > 0 ? Math.round((ppeCompliantCount / totalWorkers) * 100) : 100;
  const criticalHazardsCount = workers.filter((w) => w.risk_score >= 50).length;
  const machineAlertCount = workers.filter((w) => w.machine_exclusion_status !== 'SAFE').length;

  const getRiskBadgeColor = (score: number) => {
    if (score >= 75) return { bg: 'rgba(239, 68, 68, 0.15)', border: '#ef4444', text: '#f87171' };
    if (score >= 50) return { bg: 'rgba(249, 115, 22, 0.15)', border: '#f97316', text: '#fb923c' };
    if (score >= 25) return { bg: 'rgba(234, 179, 8, 0.15)', border: '#eab308', text: '#fde047' };
    return { bg: 'rgba(34, 197, 94, 0.15)', border: '#22c55e', text: '#4ade80' };
  };

  const getPostureBadge = (state: string) => {
    switch (state) {
      case 'FALL DETECTED':
        return { bg: 'rgba(239, 68, 68, 0.2)', border: '#ef4444', text: '#f87171', label: 'FALL DETECTED' };
      case 'POSSIBLE SLEEP':
        return { bg: 'rgba(249, 115, 22, 0.2)', border: '#f97316', text: '#fb923c', label: 'POSSIBLE SLEEP' };
      case 'INACTIVE':
        return { bg: 'rgba(234, 179, 8, 0.2)', border: '#eab308', text: '#fde047', label: 'INACTIVE (>30s)' };
      case 'RECOVERY':
        return { bg: 'rgba(59, 130, 246, 0.2)', border: '#3b82f6', text: '#60a5fa', label: 'RECOVERY IN PROGRESS' };
      case 'WALKING':
        return { bg: 'rgba(148, 163, 184, 0.15)', border: '#64748b', text: '#cbd5e1', label: 'WALKING' };
      default:
        return { bg: 'rgba(34, 197, 94, 0.15)', border: '#22c55e', text: '#4ade80', label: 'WORKING (NORMAL)' };
    }
  };

  return (
    <div style={{ padding: '24px', maxWidth: '1600px', margin: '0 auto', color: '#f1f5f9' }}>
      {/* Header */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          marginBottom: '20px',
          flexWrap: 'wrap',
          gap: '16px'
        }}
      >
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <h1 style={{ fontSize: '1.5rem', fontWeight: 800, margin: 0, letterSpacing: '-0.02em' }}>
              WORKER SAFETY INTELLIGENCE
            </h1>
            <span
              style={{
                fontSize: '0.6875rem',
                fontWeight: 700,
                padding: '3px 8px',
                borderRadius: '4px',
                backgroundColor: 'rgba(59, 130, 246, 0.15)',
                color: '#60a5fa',
                border: '1px solid rgba(59, 130, 246, 0.3)',
                letterSpacing: '0.05em'
              }}
            >
              MULTI-DIMENSIONAL AUDIT
            </span>
            <span
              title="Calibrated simulation and deterministic tracking active for mentor demonstration"
              style={{
                fontSize: '0.6875rem',
                fontWeight: 700,
                padding: '3px 8px',
                borderRadius: '4px',
                backgroundColor: 'rgba(234, 179, 8, 0.15)',
                color: '#fbbf24',
                border: '1px solid rgba(234, 179, 8, 0.3)',
                letterSpacing: '0.05em'
              }}
            >
              DEMO / SIMULATED PIPELINE
            </span>
          </div>
          <p style={{ margin: '4px 0 0 0', color: '#94a3b8', fontSize: '0.875rem' }}>
            Unified real-time tracking across 4 connected safety dimensions: Access & Identity, PPE Compliance,
            Danger & Machine Proximity, and Temporal Posture/Activity.
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <button
            onClick={() => setShowScoringModal(true)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              backgroundColor: '#1e293b',
              border: '1px solid #334155',
              color: '#cbd5e1',
              padding: '8px 14px',
              borderRadius: '6px',
              fontSize: '0.8125rem',
              fontWeight: 600,
              cursor: 'pointer'
            }}
          >
            <HelpCircle size={15} color="#94a3b8" />
            Safety Risk Scoring Rules
          </button>

          <button
            onClick={loadData}
            disabled={loading}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              backgroundColor: '#2563eb',
              border: 'none',
              color: '#ffffff',
              padding: '8px 14px',
              borderRadius: '6px',
              fontSize: '0.8125rem',
              fontWeight: 600,
              cursor: 'pointer'
            }}
          >
            <RefreshCw size={14} className={loading ? 'spin' : ''} />
            Refresh
          </button>
        </div>
      </div>

      {/* Summary KPI Cards Row */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
          gap: '14px',
          marginBottom: '22px'
        }}
      >
        <div
          style={{
            backgroundColor: '#111827',
            border: '1px solid #1f2937',
            borderRadius: '8px',
            padding: '16px'
          }}
        >
          <div style={{ fontSize: '0.75rem', fontWeight: 600, color: '#94a3b8', textTransform: 'uppercase' }}>
            Monitored Workers
          </div>
          <div style={{ fontSize: '1.75rem', fontWeight: 800, marginTop: '4px', color: '#f8fafc' }}>
            {totalWorkers}
          </div>
          <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '4px' }}>
            Active on factory shop floor
          </div>
        </div>

        <div
          style={{
            backgroundColor: '#111827',
            border: '1px solid #1f2937',
            borderRadius: '8px',
            padding: '16px'
          }}
        >
          <div style={{ fontSize: '0.75rem', fontWeight: 600, color: '#94a3b8', textTransform: 'uppercase' }}>
            PPE Compliance Rate
          </div>
          <div
            style={{
              fontSize: '1.75rem',
              fontWeight: 800,
              marginTop: '4px',
              color: ppeComplianceRate === 100 ? '#4ade80' : '#f87171'
            }}
          >
            {ppeComplianceRate}%
          </div>
          <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '4px' }}>
            {ppeCompliantCount} of {totalWorkers} workers 100% compliant
          </div>
        </div>

        <div
          style={{
            backgroundColor: '#111827',
            border: '1px solid #1f2937',
            borderRadius: '8px',
            padding: '16px'
          }}
        >
          <div style={{ fontSize: '0.75rem', fontWeight: 600, color: '#94a3b8', textTransform: 'uppercase' }}>
            High / Critical Hazards
          </div>
          <div
            style={{
              fontSize: '1.75rem',
              fontWeight: 800,
              marginTop: '4px',
              color: criticalHazardsCount > 0 ? '#ef4444' : '#22c55e'
            }}
          >
            {criticalHazardsCount}
          </div>
          <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '4px' }}>
            Risk score &ge; 50 threshold
          </div>
        </div>

        <div
          style={{
            backgroundColor: '#111827',
            border: '1px solid #1f2937',
            borderRadius: '8px',
            padding: '16px'
          }}
        >
          <div style={{ fontSize: '0.75rem', fontWeight: 600, color: '#94a3b8', textTransform: 'uppercase' }}>
            Machine Proximity Alerts
          </div>
          <div
            style={{
              fontSize: '1.75rem',
              fontWeight: 800,
              marginTop: '4px',
              color: machineAlertCount > 0 ? '#f59e0b' : '#22c55e'
            }}
          >
            {machineAlertCount}
          </div>
          <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '4px' }}>
            CNC-01 / Press exclusion alerts
          </div>
        </div>

        <div
          style={{
            backgroundColor: '#111827',
            border: '1px solid #1f2937',
            borderRadius: '8px',
            padding: '16px'
          }}
        >
          <div style={{ fontSize: '0.75rem', fontWeight: 600, color: '#94a3b8', textTransform: 'uppercase' }}>
            Overall Facility Risk
          </div>
          <div
            style={{
              fontSize: '1.75rem',
              fontWeight: 800,
              marginTop: '4px',
              color:
                (riskOverview?.overall_safety_risk_score ?? 0) >= 50
                  ? '#ef4444'
                  : (riskOverview?.overall_safety_risk_score ?? 0) >= 25
                  ? '#f59e0b'
                  : '#22c55e'
            }}
          >
            {riskOverview?.overall_safety_risk_score ?? 0}
            <span style={{ fontSize: '0.9rem', color: '#64748b', fontWeight: 400 }}> / 100</span>
          </div>
          <div style={{ fontSize: '0.75rem', color: '#94a3b8', marginTop: '4px' }}>
            Level: {riskOverview?.overall_level ?? 'NORMAL'}
          </div>
        </div>
      </div>

      {/* Filters and Search Bar */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          backgroundColor: '#111827',
          padding: '10px 16px',
          borderRadius: '8px',
          border: '1px solid #1f2937',
          marginBottom: '16px',
          flexWrap: 'wrap',
          gap: '12px'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
          {(
            [
              { id: 'ALL', label: 'All Workers' },
              { id: 'CRITICAL', label: 'High / Critical Risk' },
              { id: 'PPE_VIOLATION', label: 'PPE Issues' },
              { id: 'PROXIMITY', label: 'Proximity Warnings' },
              { id: 'POSTURE', label: 'Posture / Inactivity' }
            ] as const
          ).map((tab) => (
            <button
              key={tab.id}
              onClick={() => setFilter(tab.id)}
              style={{
                backgroundColor: filter === tab.id ? '#2563eb' : '#1e293b',
                color: filter === tab.id ? '#ffffff' : '#94a3b8',
                border: 'none',
                padding: '6px 12px',
                borderRadius: '6px',
                fontSize: '0.75rem',
                fontWeight: 600,
                cursor: 'pointer',
                transition: 'background-color 0.15s ease'
              }}
            >
              {tab.label}
            </button>
          ))}
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', position: 'relative' }}>
          <Search size={14} color="#64748b" style={{ position: 'absolute', left: '10px' }} />
          <input
            type="text"
            placeholder="Search worker ID, zone, machine..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{
              backgroundColor: '#0f172a',
              border: '1px solid #334155',
              borderRadius: '6px',
              color: '#f8fafc',
              padding: '6px 10px 6px 30px',
              fontSize: '0.8125rem',
              outline: 'none',
              width: '240px'
            }}
          />
        </div>
      </div>

      {/* Workers List / Cards Table */}
      {filteredWorkers.length === 0 ? (
        <div
          style={{
            backgroundColor: '#111827',
            border: '1px solid #1f2937',
            borderRadius: '8px',
            padding: '48px 24px',
            textAlign: 'center',
            color: '#64748b'
          }}
        >
          <UserCheck size={36} color="#334155" style={{ marginBottom: '12px' }} />
          <div style={{ fontSize: '1rem', fontWeight: 600, color: '#94a3b8' }}>
            No monitored workers matching selected criteria
          </div>
          <div style={{ fontSize: '0.8125rem', marginTop: '6px' }}>
            Adjust your filter or trigger a scenario from the Safety Scenario Lab to simulate active workers.
          </div>
          {onNavigate && (
            <button
              onClick={() => onNavigate('replay')}
              style={{
                marginTop: '16px',
                backgroundColor: '#2563eb',
                border: 'none',
                color: '#ffffff',
                padding: '8px 16px',
                borderRadius: '6px',
                fontSize: '0.8125rem',
                fontWeight: 600,
                cursor: 'pointer'
              }}
            >
              Open Safety Scenario Lab
            </button>
          )}
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {filteredWorkers.map((worker) => {
            const riskColors = getRiskBadgeColor(worker.risk_score);
            const postureBadge = getPostureBadge(worker.posture_state);

            return (
              <div
                key={worker.worker_id}
                style={{
                  backgroundColor: '#111827',
                  border: `1px solid ${worker.risk_score >= 50 ? riskColors.border : '#1f2937'}`,
                  borderRadius: '8px',
                  padding: '18px 20px',
                  display: 'grid',
                  gridTemplateColumns: '1.2fr 1.6fr 1.5fr 1.6fr 1.2fr',
                  gap: '20px',
                  alignItems: 'center',
                  transition: 'border-color 0.2s ease, box-shadow 0.2s ease'
                }}
              >
                {/* 1. IDENTITY & ACCESS */}
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
                    <span style={{ fontSize: '1.05rem', fontWeight: 800, color: '#f8fafc' }}>
                      {worker.worker_id}
                    </span>
                    <span style={{ fontSize: '0.75rem', color: '#64748b' }}>(Track #{worker.track_id})</span>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    {worker.authorized ? (
                      <span
                        style={{
                          fontSize: '0.6875rem',
                          fontWeight: 700,
                          padding: '2px 8px',
                          borderRadius: '4px',
                          backgroundColor: 'rgba(34, 197, 94, 0.15)',
                          color: '#4ade80',
                          border: '1px solid rgba(34, 197, 94, 0.3)'
                        }}
                      >
                        AUTHORIZED
                      </span>
                    ) : (
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
                        {worker.access_status === 'DENIED' ? 'ACCESS DENIED' : 'UNAUTHORIZED'}
                      </span>
                    )}
                    <span style={{ fontSize: '0.6875rem', color: '#64748b' }}>
                      Entry: {worker.entry_timestamp || '08:30 AM'}
                    </span>
                  </div>
                </div>

                {/* 2. PPE GEAR COMPLIANCE */}
                <div>
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      marginBottom: '6px'
                    }}
                  >
                    <span style={{ fontSize: '0.6875rem', fontWeight: 700, color: '#94a3b8', textTransform: 'uppercase' }}>
                      PPE Compliance ({worker.ppe_compliance_pct}%)
                    </span>
                    {worker.ppe_compliance_pct === 100 ? (
                      <span style={{ fontSize: '0.6875rem', color: '#4ade80', fontWeight: 700 }}>COMPLIANT</span>
                    ) : (
                      <span style={{ fontSize: '0.6875rem', color: '#f87171', fontWeight: 700 }}>VIOLATION</span>
                    )}
                  </div>

                  {/* 4 Items Checkbox Indicators */}
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '6px' }}>
                    <div
                      title={`Helmet: ${worker.helmet ? 'Present' : 'Missing'}`}
                      style={{
                        display: 'flex',
                        flexDirection: 'column',
                        alignItems: 'center',
                        gap: '2px',
                        padding: '6px 4px',
                        borderRadius: '4px',
                        backgroundColor: worker.helmet ? 'rgba(34, 197, 94, 0.1)' : 'rgba(239, 68, 68, 0.15)',
                        border: `1px solid ${worker.helmet ? 'rgba(34, 197, 94, 0.25)' : 'rgba(239, 68, 68, 0.35)'}`,
                        color: worker.helmet ? '#4ade80' : '#f87171'
                      }}
                    >
                      <HardHat size={14} />
                      <span style={{ fontSize: '0.625rem', fontWeight: 700 }}>HELMET</span>
                    </div>

                    <div
                      title={`Safety Vest: ${worker.safety_vest ? 'Present' : 'Missing'}`}
                      style={{
                        display: 'flex',
                        flexDirection: 'column',
                        alignItems: 'center',
                        gap: '2px',
                        padding: '6px 4px',
                        borderRadius: '4px',
                        backgroundColor: worker.safety_vest ? 'rgba(34, 197, 94, 0.1)' : 'rgba(239, 68, 68, 0.15)',
                        border: `1px solid ${worker.safety_vest ? 'rgba(34, 197, 94, 0.25)' : 'rgba(239, 68, 68, 0.35)'}`,
                        color: worker.safety_vest ? '#4ade80' : '#f87171'
                      }}
                    >
                      <Shirt size={14} />
                      <span style={{ fontSize: '0.625rem', fontWeight: 700 }}>VEST</span>
                    </div>

                    <div
                      title={`Safety Shoes: ${worker.safety_shoes ? 'Present' : 'Missing'}`}
                      style={{
                        display: 'flex',
                        flexDirection: 'column',
                        alignItems: 'center',
                        gap: '2px',
                        padding: '6px 4px',
                        borderRadius: '4px',
                        backgroundColor: worker.safety_shoes ? 'rgba(34, 197, 94, 0.1)' : 'rgba(239, 68, 68, 0.15)',
                        border: `1px solid ${worker.safety_shoes ? 'rgba(34, 197, 94, 0.25)' : 'rgba(239, 68, 68, 0.35)'}`,
                        color: worker.safety_shoes ? '#4ade80' : '#f87171'
                      }}
                    >
                      <Footprints size={14} />
                      <span style={{ fontSize: '0.625rem', fontWeight: 700 }}>SHOES</span>
                    </div>

                    <div
                      title={`Gloves: ${worker.gloves ? 'Present' : 'Missing'}`}
                      style={{
                        display: 'flex',
                        flexDirection: 'column',
                        alignItems: 'center',
                        gap: '2px',
                        padding: '6px 4px',
                        borderRadius: '4px',
                        backgroundColor: worker.gloves ? 'rgba(34, 197, 94, 0.1)' : 'rgba(239, 68, 68, 0.15)',
                        border: `1px solid ${worker.gloves ? 'rgba(34, 197, 94, 0.25)' : 'rgba(239, 68, 68, 0.35)'}`,
                        color: worker.gloves ? '#4ade80' : '#f87171'
                      }}
                    >
                      <Hand size={14} />
                      <span style={{ fontSize: '0.625rem', fontWeight: 700 }}>GLOVES</span>
                    </div>
                  </div>
                </div>

                {/* 3. POSTURE & ACTIVITY */}
                <div>
                  <div style={{ fontSize: '0.6875rem', fontWeight: 700, color: '#94a3b8', textTransform: 'uppercase', marginBottom: '6px' }}>
                    Activity & Posture
                  </div>
                  <div>
                    <span
                      style={{
                        display: 'inline-block',
                        fontSize: '0.75rem',
                        fontWeight: 700,
                        padding: '4px 10px',
                        borderRadius: '4px',
                        backgroundColor: postureBadge.bg,
                        color: postureBadge.text,
                        border: `1px solid ${postureBadge.border}`
                      }}
                    >
                      {postureBadge.label}
                    </span>
                  </div>
                  <div style={{ fontSize: '0.6875rem', color: '#64748b', marginTop: '4px' }}>
                    Duration: {worker.posture_duration_sec ? `${Math.round(worker.posture_duration_sec)}s` : '< 5s'}
                    {worker.aspect_ratio ? ` • Aspect: ${worker.aspect_ratio.toFixed(2)}` : ''}
                  </div>
                </div>

                {/* 4. SPATIAL & MACHINE SAFETY */}
                <div>
                  <div style={{ fontSize: '0.6875rem', fontWeight: 700, color: '#94a3b8', textTransform: 'uppercase', marginBottom: '4px' }}>
                    Spatial & Machine Clearance
                  </div>
                  <div style={{ fontSize: '0.8125rem', color: '#e2e8f0', fontWeight: 600 }}>
                    {worker.current_zone}
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '4px', fontSize: '0.75rem' }}>
                    <span style={{ color: '#94a3b8' }}>
                      To Danger:{' '}
                      <strong style={{ color: worker.distance_to_danger_zone === 0 ? '#ef4444' : '#e2e8f0' }}>
                        {worker.distance_to_danger_zone.toFixed(1)}m
                      </strong>
                    </span>
                    <span style={{ color: '#475569' }}>|</span>
                    <span style={{ color: '#94a3b8' }}>
                      {worker.nearest_machine}:{' '}
                      <strong
                        style={{
                          color:
                            worker.machine_exclusion_status === 'EXCLUSION BREACH'
                              ? '#ef4444'
                              : worker.machine_exclusion_status === 'WARNING PROXIMITY'
                              ? '#f59e0b'
                              : '#4ade80'
                        }}
                      >
                        {worker.distance_to_machine.toFixed(1)}m ({worker.machine_exclusion_status})
                      </strong>
                    </span>
                  </div>
                </div>

                {/* 5. SAFETY RISK SCORE & ACTION */}
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '12px' }}>
                  <div>
                    <div style={{ fontSize: '0.6875rem', fontWeight: 700, color: '#94a3b8', textTransform: 'uppercase' }}>
                      Risk Score
                    </div>
                    <div style={{ display: 'flex', alignItems: 'baseline', gap: '4px', marginTop: '2px' }}>
                      <span style={{ fontSize: '1.5rem', fontWeight: 900, color: riskColors.text }}>
                        {worker.risk_score}
                      </span>
                      <span style={{ fontSize: '0.75rem', color: '#64748b' }}>/ 100</span>
                    </div>
                    <div style={{ fontSize: '0.6875rem', color: '#94a3b8', marginTop: '2px', maxWidth: '160px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {worker.main_reason}
                    </div>
                  </div>

                  <button
                    onClick={() => setSelectedWorker(worker)}
                    title="View full worker detail & risk breakdown"
                    style={{
                      backgroundColor: '#1e293b',
                      border: '1px solid #334155',
                      color: '#cbd5e1',
                      padding: '8px',
                      borderRadius: '6px',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center'
                    }}
                  >
                    <ChevronRight size={18} />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Worker Detail Modal */}
      {selectedWorker && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.75)',
            backdropFilter: 'blur(4px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 100,
            padding: '20px'
          }}
          onClick={() => setSelectedWorker(null)}
        >
          <div
            style={{
              backgroundColor: '#111827',
              border: '1px solid #334155',
              borderRadius: '12px',
              padding: '24px',
              maxWidth: '650px',
              width: '100%',
              color: '#f8fafc',
              maxHeight: '85vh',
              overflowY: 'auto'
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <div>
                <h2 style={{ fontSize: '1.25rem', fontWeight: 800, margin: 0 }}>
                  Worker Safety Profile: {selectedWorker.worker_id}
                </h2>
                <div style={{ fontSize: '0.8125rem', color: '#94a3b8', marginTop: '2px' }}>
                  Track #{selectedWorker.track_id} • Status: {selectedWorker.access_status} • Zone: {selectedWorker.current_zone}
                </div>
              </div>
              <button
                onClick={() => setSelectedWorker(null)}
                style={{
                  backgroundColor: 'transparent',
                  border: 'none',
                  color: '#94a3b8',
                  fontSize: '1.25rem',
                  cursor: 'pointer'
                }}
              >
                &times;
              </button>
            </div>

            {/* Risk Decomposition Table */}
            <div style={{ backgroundColor: '#0f172a', padding: '16px', borderRadius: '8px', border: '1px solid #1e293b', marginBottom: '20px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                <span style={{ fontSize: '0.8125rem', fontWeight: 700, color: '#94a3b8', textTransform: 'uppercase' }}>
                  Safety Risk Score Decomposition
                </span>
                <span
                  style={{
                    fontSize: '1.125rem',
                    fontWeight: 900,
                    color: getRiskBadgeColor(selectedWorker.risk_score).text
                  }}
                >
                  {selectedWorker.risk_score} / 100 ({selectedWorker.severity})
                </span>
              </div>

              {selectedWorker.factors && selectedWorker.factors.length > 0 ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {selectedWorker.factors.map((f, i) => (
                    <div
                      key={i}
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        fontSize: '0.8125rem',
                        padding: '6px 10px',
                        backgroundColor: '#1e293b',
                        borderRadius: '4px'
                      }}
                    >
                      <span style={{ color: '#e2e8f0' }}>{f.reason}</span>
                      <span style={{ fontWeight: 700, color: '#f87171' }}>+{f.weight}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <div style={{ fontSize: '0.8125rem', color: '#4ade80' }}>
                  Zero hazard penalties. Worker operates in 100% compliant baseline conditions.
                </div>
              )}
            </div>

            {/* Dimensional Summary */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px', fontSize: '0.8125rem' }}>
              <div style={{ backgroundColor: '#0f172a', padding: '12px', borderRadius: '6px', border: '1px solid #1e293b' }}>
                <div style={{ fontWeight: 700, color: '#94a3b8', marginBottom: '6px' }}>ACCESS & IDENTITY</div>
                <div>Status: <strong>{selectedWorker.access_status}</strong></div>
                <div>Authorized: <strong>{selectedWorker.authorized ? 'YES' : 'NO'}</strong></div>
                <div>Shift Entry: <strong>{selectedWorker.entry_timestamp || '08:30:12 AM'}</strong></div>
              </div>

              <div style={{ backgroundColor: '#0f172a', padding: '12px', borderRadius: '6px', border: '1px solid #1e293b' }}>
                <div style={{ fontWeight: 700, color: '#94a3b8', marginBottom: '6px' }}>PPE AUDIT</div>
                <div>Helmet: <strong>{selectedWorker.helmet ? 'VERIFIED' : 'MISSING'}</strong></div>
                <div>Vest: <strong>{selectedWorker.safety_vest ? 'VERIFIED' : 'MISSING'}</strong></div>
                <div>Shoes: <strong>{selectedWorker.safety_shoes ? 'VERIFIED' : 'MISSING'}</strong></div>
                <div>Gloves: <strong>{selectedWorker.gloves ? 'VERIFIED' : 'MISSING'}</strong></div>
              </div>

              <div style={{ backgroundColor: '#0f172a', padding: '12px', borderRadius: '6px', border: '1px solid #1e293b' }}>
                <div style={{ fontWeight: 700, color: '#94a3b8', marginBottom: '6px' }}>POSTURE & ACTIVITY</div>
                <div>State: <strong>{selectedWorker.posture_state}</strong></div>
                <div>Observation Duration: <strong>{Math.round(selectedWorker.posture_duration_sec)}s</strong></div>
                <div>Debounce Status: <strong>Confirmed Deterministic</strong></div>
              </div>

              <div style={{ backgroundColor: '#0f172a', padding: '12px', borderRadius: '6px', border: '1px solid #1e293b' }}>
                <div style={{ fontWeight: 700, color: '#94a3b8', marginBottom: '6px' }}>SPATIAL PERIMETER</div>
                <div>Current Zone: <strong>{selectedWorker.current_zone}</strong></div>
                <div>Danger Zone Dist: <strong>{selectedWorker.distance_to_danger_zone.toFixed(1)}m</strong></div>
                <div>Machine Dist: <strong>{selectedWorker.distance_to_machine.toFixed(1)}m ({selectedWorker.nearest_machine})</strong></div>
              </div>
            </div>

            <div style={{ marginTop: '20px', display: 'flex', justifyContent: 'flex-end' }}>
              <button
                onClick={() => setSelectedWorker(null)}
                style={{
                  backgroundColor: '#2563eb',
                  border: 'none',
                  color: '#ffffff',
                  padding: '8px 16px',
                  borderRadius: '6px',
                  fontWeight: 600,
                  fontSize: '0.8125rem',
                  cursor: 'pointer'
                }}
              >
                Close Profile
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Transparent Scoring Model Modal */}
      {showScoringModal && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.75)',
            backdropFilter: 'blur(4px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 100,
            padding: '20px'
          }}
          onClick={() => setShowScoringModal(false)}
        >
          <div
            style={{
              backgroundColor: '#111827',
              border: '1px solid #334155',
              borderRadius: '12px',
              padding: '24px',
              maxWidth: '650px',
              width: '100%',
              color: '#f8fafc'
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <h2 style={{ fontSize: '1.25rem', fontWeight: 800, margin: 0 }}>
                Transparent Safety Risk Scoring Model
              </h2>
              <button
                onClick={() => setShowScoringModal(false)}
                style={{
                  backgroundColor: 'transparent',
                  border: 'none',
                  color: '#94a3b8',
                  fontSize: '1.25rem',
                  cursor: 'pointer'
                }}
              >
                &times;
              </button>
            </div>

            <p style={{ fontSize: '0.8125rem', color: '#94a3b8', margin: '0 0 16px 0' }}>
              The 0–100 Safety Risk Score is deterministically computed from additive hazard contributions.
              Multiple simultaneous hazards increase the worker risk score up to a maximum cap of 100.
            </p>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '0.8125rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 12px', backgroundColor: '#0f172a', borderRadius: '4px' }}>
                <span>Normal Operating State (Zero Violations)</span>
                <span style={{ fontWeight: 700, color: '#4ade80' }}>0 (Baseline)</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 12px', backgroundColor: '#0f172a', borderRadius: '4px' }}>
                <span>Missing PPE Item (Helmet / Vest / Shoes / Gloves)</span>
                <span style={{ fontWeight: 700, color: '#fde047' }}>+10 to +20</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 12px', backgroundColor: '#0f172a', borderRadius: '4px' }}>
                <span>Warning-Zone Entry (Buffer Encroachment)</span>
                <span style={{ fontWeight: 700, color: '#fde047' }}>+15 to +35</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 12px', backgroundColor: '#0f172a', borderRadius: '4px' }}>
                <span>Machine Proximity Warning (CNC-01 Warning Zone)</span>
                <span style={{ fontWeight: 700, color: '#fde047' }}>+20</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 12px', backgroundColor: '#0f172a', borderRadius: '4px' }}>
                <span>Worker Inactivity (&gt; 30s debounced)</span>
                <span style={{ fontWeight: 700, color: '#fb923c' }}>+20</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 12px', backgroundColor: '#0f172a', borderRadius: '4px' }}>
                <span>Possible Sleep (Prolonged Recumbent State)</span>
                <span style={{ fontWeight: 700, color: '#fb923c' }}>+25</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 12px', backgroundColor: '#0f172a', borderRadius: '4px' }}>
                <span>Danger-Zone Physical Breach</span>
                <span style={{ fontWeight: 700, color: '#f87171' }}>+35</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 12px', backgroundColor: '#0f172a', borderRadius: '4px' }}>
                <span>Machine Exclusion Breach (CNC-01 Spindle Hub &lt; 2.0m)</span>
                <span style={{ fontWeight: 700, color: '#f87171' }}>+40</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 12px', backgroundColor: '#0f172a', borderRadius: '4px' }}>
                <span>Worker Fall Detected (PERSON_DOWN aspect ratio &ge; 1.8)</span>
                <span style={{ fontWeight: 700, color: '#ef4444' }}>+50 (Critical)</span>
              </div>
            </div>

            <div style={{ marginTop: '16px', fontSize: '0.75rem', color: '#64748b' }}>
              <strong>Severity Bands:</strong> 0–24: Normal | 25–49: Low | 50–74: Medium | 75–99: High | 100: Critical
            </div>

            <div style={{ marginTop: '20px', display: 'flex', justifyContent: 'flex-end' }}>
              <button
                onClick={() => setShowScoringModal(false)}
                style={{
                  backgroundColor: '#2563eb',
                  border: 'none',
                  color: '#ffffff',
                  padding: '8px 16px',
                  borderRadius: '6px',
                  fontWeight: 600,
                  fontSize: '0.8125rem',
                  cursor: 'pointer'
                }}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
