/**
 * WorkSafe AI — Live Safety Command Center Types (Experiment 08).
 * 
 * Strict TypeScript models for events, system telemetry, watchdog health,
 * and live pipeline metrics. No biometrics or PII are supported or stored.
 */

export type SafetyState = 'NORMAL' | 'WARNING' | 'DANGER' | 'RECOVERY' | 'UNKNOWN';

export type EventSeverity = 'CRITICAL' | 'WARNING' | 'SYSTEM' | 'INFO';

export type LifecycleStatus = 'OPEN' | 'ACKNOWLEDGED' | 'RESOLVED';

export type AcknowledgementStatus = 'UNACKNOWLEDGED' | 'ACKNOWLEDGED';

export interface SafetyEvent {
  event_id: string;
  event_type: string;
  timestamp: number;
  camera_id: string;
  safety_state: SafetyState;
  severity: EventSeverity;
  zone_id?: string | null;
  track_id?: number | null;
  worker_id?: string | null;
  world_position?: [number, number] | null;
  source: string;
  configuration_version: string;
  lifecycle_status: LifecycleStatus;
  acknowledgement_status: AcknowledgementStatus;
  acknowledged_at?: number | null;
  acknowledged_by?: string | null;
  acknowledgement_note?: string | null;
  resolved_at?: number | null;
  resolved_by?: string | null;
  resolution_reason?: string | null;
  parent_event_id?: string | null;
  description: string;
  // Prompt 2 Extensions
  confidence?: number;
  location?: string;
  risk_contribution?: number;
  evidence?: string;
  status?: string;
}

export interface WorkerSafetyProfile {
  worker_id: string;
  track_id: number;
  access_status: 'AUTHORIZED' | 'UNAUTHORIZED' | 'DENIED' | 'PENDING';
  authorized: boolean;
  entry_timestamp: string;
  helmet: boolean;
  safety_vest: boolean;
  safety_shoes: boolean;
  gloves: boolean;
  ppe_compliance_pct: number;
  posture_state: 'NORMAL' | 'WALKING' | 'STANDING' | 'WORKING' | 'INACTIVE' | 'POSSIBLE SLEEP' | 'FALL DETECTED' | 'RECOVERY' | string;
  aspect_ratio?: number;
  posture_duration_sec: number;
  current_zone: string;
  distance_to_danger_zone: number;
  nearest_machine: string;
  distance_to_machine: number;
  machine_exclusion_status: 'SAFE' | 'WARNING PROXIMITY' | 'EXCLUSION BREACH';
  risk_score: number;
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'NORMAL';
  main_reason: string;
  world_pos?: [number, number];
  factors?: Array<{ factor_name: string; weight: number; reason: string }>;
}

export interface RiskOverview {
  overall_safety_risk_score: number;
  overall_level: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'NORMAL';
  active_workers_count: number;
  top_risk_factors: string[];
  workers: Record<string, any>;
  scoring_rules: Record<string, number>;
  disclaimer: string;
}

export interface ScenarioCatalogItem {
  id: string;
  name: string;
  description: string;
  domain: string;
  severity: 'CRITICAL' | 'WARNING' | 'INFO';
}

export interface ScenarioStepResult {
  scenario: string;
  status: string;
  message: string;
  emitted_events: SafetyEvent[];
  risk_assessment?: any;
  active_workers?: WorkerSafetyProfile[];
  execution_time_ms: number;
  step?: number;
  total_steps?: number;
}

export type EventLifecycleStage = 'DETECTED' | 'WARNING' | 'DANGER' | 'ACKNOWLEDGED' | 'RESOLVED';

export interface ActiveTrack {
  track_id: number;
  bbox: [number, number, number, number];
  confidence?: number;
  world_pos: [number, number] | null;
  state: SafetyState;
}

export interface StreamStatus {
  is_running: boolean;
  camera_id: string;
  current_frame_id: number;
  total_frames: number;
  pipeline_fps: number;
  latency_ms: number;
  safety_state: SafetyState;
  active_tracks_count: number;
  active_tracks: ActiveTrack[];
  source_mode: string;
  source_file: string;
  telemetry?: Record<string, any>;
  timings?: Record<string, number>;
}

export interface SystemHealth {
  status: 'READY' | 'DEGRADED' | 'UNKNOWN';
  overall_safety_state: SafetyState;
  pipeline_fps: number;
  latency_ms: number;
  active_tracks_count: number;
  camera_id: string;
  source_mode: string;
  components: Record<string, 'AVAILABLE' | 'UNAVAILABLE' | 'HEALTHY' | 'DEGRADED' | 'UNKNOWN'>;
  environment: {
    os: string;
    cpu: string;
    python_version: string;
    ram_total_gb: number;
    ram_available_gb: number;
    device: string;
  };
  disclaimer: string;
}

export interface CameraHealth {
  camera_id: string;
  health_state: 'HEALTHY' | 'DEGRADED' | 'UNKNOWN';
  effective_fps: number;
  frozen_frame_count: number;
  consecutive_drops: number;
  queue_depth: number;
  max_queue_depth: number;
  processing_latency_ms: number;
  inter_frame_gap_ms: number;
  last_frame_id: number;
  failure_reasons: string[];
}
