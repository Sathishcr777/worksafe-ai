/**
 * WorkSafe AI — REST API Client (Experiment 08).
 * 
 * Typed methods for querying system health, camera diagnostics, active alerts,
 * event audit log, and triggering operator acknowledgement actions.
 */

import type {
  SafetyEvent,
  SafetyState,
  StreamStatus,
  SystemHealth,
  CameraHealth,
  EventSeverity,
  LifecycleStatus
} from '../types';

const BASE_URL = '';

export async function fetchStreamStatus(): Promise<StreamStatus> {
  const res = await fetch(`${BASE_URL}/api/stream/status`);
  if (!res.ok) throw new Error(`Stream status failed: ${res.statusText}`);
  return res.json();
}

export async function startDemoPipeline(): Promise<{ status: string; is_running: boolean }> {
  const res = await fetch(`${BASE_URL}/api/demo/start`, { method: 'POST' });
  if (!res.ok) throw new Error(`Start demo failed: ${res.statusText}`);
  return res.json();
}

export async function stopDemoPipeline(): Promise<{ status: string; is_running: boolean }> {
  const res = await fetch(`${BASE_URL}/api/demo/stop`, { method: 'POST' });
  if (!res.ok) throw new Error(`Stop demo failed: ${res.statusText}`);
  return res.json();
}

export async function restartDemoPipeline(): Promise<{ status: string; is_running: boolean }> {
  const res = await fetch(`${BASE_URL}/api/demo/restart`, { method: 'POST' });
  if (!res.ok) throw new Error(`Restart demo failed: ${res.statusText}`);
  return res.json();
}

export async function seekDemoPipeline(frame: number): Promise<{
  status: string;
  frame: number;
  safety_state?: SafetyState;
  is_running?: boolean;
  total_frames?: number;
}> {
  const res = await fetch(`${BASE_URL}/api/demo/seek?frame=${encodeURIComponent(frame)}`, { method: 'POST' });
  if (!res.ok) throw new Error(`Seek demo failed: ${res.statusText}`);
  return res.json();
}

export async function fetchSystemHealth(): Promise<SystemHealth> {
  const res = await fetch(`${BASE_URL}/api/health/system`);
  if (!res.ok) throw new Error(`System health failed: ${res.statusText}`);
  return res.json();
}

export async function fetchCameraHealth(cameraId: string = 'cam_bay_01'): Promise<CameraHealth> {
  const res = await fetch(`${BASE_URL}/api/health/camera/${cameraId}`);
  if (!res.ok) throw new Error(`Camera health failed: ${res.statusText}`);
  return res.json();
}

export async function fetchActiveAlerts(limit: number = 50): Promise<{ count: number; alerts: SafetyEvent[] }> {
  const res = await fetch(`${BASE_URL}/api/alerts/active?limit=${limit}`);
  if (!res.ok) throw new Error(`Active alerts failed: ${res.statusText}`);
  return res.json();
}

export async function fetchEvents(params?: {
  camera_id?: string;
  severity?: EventSeverity;
  lifecycle_status?: LifecycleStatus;
  limit?: number;
  offset?: number;
}): Promise<{ total: number; limit: number; offset: number; events: SafetyEvent[] }> {
  const query = new URLSearchParams();
  if (params?.camera_id) query.set('camera_id', params.camera_id);
  if (params?.severity) query.set('severity', params.severity);
  if (params?.lifecycle_status) query.set('lifecycle_status', params.lifecycle_status);
  if (params?.limit) query.set('limit', params.limit.toString());
  if (params?.offset) query.set('offset', params.offset.toString());

  const res = await fetch(`${BASE_URL}/api/events?${query.toString()}`);
  if (!res.ok) throw new Error(`Events query failed: ${res.statusText}`);
  return res.json();
}

export async function acknowledgeEvent(
  eventId: string,
  acknowledgedBy: string = 'Safety_Supervisor',
  note: string = 'Operator verified'
): Promise<SafetyEvent> {
  const res = await fetch(`${BASE_URL}/api/events/${eventId}/acknowledge`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ acknowledged_by: acknowledgedBy, note })
  });
  if (!res.ok) throw new Error(`Acknowledge failed: ${res.statusText}`);
  return res.json();
}

export async function resolveEvent(
  eventId: string,
  resolvedBy: string = 'Safety_Supervisor',
  reason: string = 'Hazard condition cleared'
): Promise<SafetyEvent> {
  const res = await fetch(`${BASE_URL}/api/events/${eventId}/resolve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ resolved_by: resolvedBy, reason })
  });
  if (!res.ok) throw new Error(`Resolve failed: ${res.statusText}`);
  return res.json();
}

// -------------------------------------------------------------
// Safety Intelligence & Scenario API Functions (Prompt 2)
// -------------------------------------------------------------

export async function fetchSafetyRisk(): Promise<import('../types').RiskOverview> {
  const res = await fetch(`${BASE_URL}/api/safety/risk`);
  if (!res.ok) throw new Error(`Safety risk failed: ${res.statusText}`);
  return res.json();
}

export async function fetchSafetyWorkers(): Promise<{
  active_workers_count: number;
  workers: import('../types').WorkerSafetyProfile[];
  timestamp: number;
}> {
  const res = await fetch(`${BASE_URL}/api/safety/workers`);
  if (!res.ok) throw new Error(`Safety workers failed: ${res.statusText}`);
  return res.json();
}

export async function fetchSafetyPPE(): Promise<any> {
  const res = await fetch(`${BASE_URL}/api/safety/ppe`);
  if (!res.ok) throw new Error(`Safety PPE failed: ${res.statusText}`);
  return res.json();
}

export async function fetchSafetyAccess(): Promise<any> {
  const res = await fetch(`${BASE_URL}/api/safety/access`);
  if (!res.ok) throw new Error(`Safety access failed: ${res.statusText}`);
  return res.json();
}

export async function fetchSafetyMachines(): Promise<any> {
  const res = await fetch(`${BASE_URL}/api/safety/machines`);
  if (!res.ok) throw new Error(`Safety machines failed: ${res.statusText}`);
  return res.json();
}

export async function fetchScenarios(): Promise<{
  scenarios: import('../types').ScenarioCatalogItem[];
  current_scenario: string;
}> {
  const res = await fetch(`${BASE_URL}/api/scenarios`);
  if (!res.ok) throw new Error(`Fetch scenarios failed: ${res.statusText}`);
  return res.json();
}

export async function startScenario(
  scenarioName: string,
  step?: number
): Promise<import('../types').ScenarioStepResult> {
  const query = step !== undefined ? `?step=${step}` : '';
  const res = await fetch(`${BASE_URL}/api/scenarios/${encodeURIComponent(scenarioName)}/start${query}`, {
    method: 'POST'
  });
  if (!res.ok) throw new Error(`Start scenario failed: ${res.statusText}`);
  return res.json();
}

