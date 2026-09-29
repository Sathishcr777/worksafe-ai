import React, { useState, useEffect, useCallback } from 'react';
import { Sidebar } from './components/Sidebar';
import type { PageId } from './components/Sidebar';
import { Topbar } from './components/Topbar';
import { SafetyBoundaryBanner } from './components/SafetyBoundaryBanner';
import { ToastContainer } from './components/Toast';
import type { ToastMessage } from './components/Toast';
import { EventDetailModal } from './components/EventDetailModal';
import { ActionModal } from './components/ActionModal';
import { KeyboardShortcutsModal } from './components/KeyboardShortcutsModal';

// Pages
import { CommandCenterPage } from './pages/CommandCenterPage';
import { WorkerSafetyPage } from './pages/WorkerSafetyPage';
import { LiveMonitoringPage } from './pages/LiveMonitoringPage';
import { CamerasPage } from './pages/CamerasPage';
import { AlertsPage } from './pages/AlertsPage';
import { EventHistoryPage } from './pages/EventHistoryPage';
import { AnalyticsPage } from './pages/AnalyticsPage';
import { SystemHealthPage } from './pages/SystemHealthPage';
import { ReplayScenariosPage } from './pages/ReplayScenariosPage';
import { ReportsPage } from './pages/ReportsPage';
import { SettingsPage } from './pages/SettingsPage';

// Services & Types
import {
  fetchStreamStatus,
  fetchSystemHealth,
  fetchCameraHealth,
  fetchActiveAlerts,
  fetchEvents,
  startDemoPipeline,
  stopDemoPipeline,
  restartDemoPipeline,
  seekDemoPipeline,
  acknowledgeEvent,
  resolveEvent
} from './services/api';
import { liveSocket } from './services/websocket';
import type { ConnectionState } from './services/websocket';
import type { SafetyState, StreamStatus, SystemHealth, CameraHealth, SafetyEvent } from './types';
import { AlertTriangle } from 'lucide-react';

export const App: React.FC = () => {
  // Page Routing State (Hash-based)
  const [currentPage, setCurrentPage] = useState<PageId>('command-center');

  // Master Safety & Telemetry State
  const [safetyState, setSafetyState] = useState<SafetyState>('NORMAL');
  const [connectionState, setConnectionState] = useState<ConnectionState>('DISCONNECTED');
  const [streamStatus, setStreamStatus] = useState<StreamStatus | null>(null);
  const [systemHealth, setSystemHealth] = useState<SystemHealth | null>(null);
  const [cameraHealth, setCameraHealth] = useState<CameraHealth | null>(null);
  const [activeAlerts, setActiveAlerts] = useState<SafetyEvent[]>([]);
  const [events, setEvents] = useState<SafetyEvent[]>([]);
  const [liveWebSocketEvents, setLiveWebSocketEvents] = useState<SafetyEvent[]>([]);

  // Modals & User Feedback
  const [selectedEvent, setSelectedEvent] = useState<SafetyEvent | null>(null);
  const [shortcutsModalOpen, setShortcutsModalOpen] = useState(false);
  const [actionModal, setActionModal] = useState<{
    type: 'acknowledge' | 'resolve' | null;
    eventId: string | null;
  }>({ type: null, eventId: null });
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  const addToast = useCallback((type: ToastMessage['type'], title: string, message?: string) => {
    const id = `toast-${Date.now()}-${Math.random().toString(36).substr(2, 4)}`;
    setToasts((prev) => [...prev, { id, type, title, message }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 4000);
  }, []);

  const dismissToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  // Hash Routing Sync
  useEffect(() => {
    const handleHashChange = () => {
      const hash = window.location.hash.replace(/^#\/?/, '').toLowerCase();
      const validPages: PageId[] = [
        'command-center',
        'worker-safety',
        'monitoring',
        'cameras',
        'alerts',
        'history',
        'analytics',
        'health',
        'replay',
        'reports',
        'settings'
      ];
      if (validPages.includes(hash as PageId)) {
        setCurrentPage(hash as PageId);
      } else if (!hash) {
        setCurrentPage('command-center');
      }
    };

    handleHashChange();
    window.addEventListener('hashchange', handleHashChange);
    return () => window.removeEventListener('hashchange', handleHashChange);
  }, []);

  const navigateTo = useCallback((page: PageId | string) => {
    window.location.hash = `#/${page}`;
    setCurrentPage(page as PageId);
  }, []);

  // Refresh active alerts and historical events
  const loadAlertsAndEvents = useCallback(async () => {
    try {
      const alertData = await fetchActiveAlerts();
      setActiveAlerts(alertData.alerts);

      const eventData = await fetchEvents({ limit: 150 });
      setEvents(eventData.events);
    } catch (err) {
      console.warn('Failed to refresh alerts/events:', err);
    }
  }, []);

  // Poll stream & health metrics
  const pollStatus = useCallback(async () => {
    try {
      const s = await fetchStreamStatus();
      setStreamStatus(s);
      if (s.safety_state) {
        setSafetyState(s.safety_state);
      }
    } catch (err) {
      console.warn('Stream status poll error:', err);
    }

    try {
      const sh = await fetchSystemHealth();
      setSystemHealth(sh);
    } catch (err) {
      console.warn('System health poll error:', err);
    }

    try {
      const ch = await fetchCameraHealth('cam_bay_01');
      setCameraHealth(ch);
      if (ch.health_state === 'UNKNOWN') {
        setSafetyState('UNKNOWN');
      }
    } catch (err) {
      console.warn('Camera health poll error:', err);
    }
  }, []);

  // Initialize and register WebSocket listener
  useEffect(() => {
    pollStatus();
    loadAlertsAndEvents();

    const pollInterval = setInterval(pollStatus, 1000);

    const unsubState = liveSocket.onStateChange((state) => {
      setConnectionState(state);
    });

    const unsubEvent = liveSocket.onEvent((newEvent) => {
      // Buffer in live WS feed
      setLiveWebSocketEvents((prev) => [newEvent, ...prev.slice(0, 99)]);
      // Append to global events list
      setEvents((prev) => [newEvent, ...prev.slice(0, 199)]);

      if (newEvent.severity === 'CRITICAL' || newEvent.severity === 'WARNING' || newEvent.severity === 'SYSTEM') {
        loadAlertsAndEvents();
        if (newEvent.severity === 'CRITICAL') {
          addToast('error', `CRITICAL BREACH: ${newEvent.event_type}`, `Track #${newEvent.track_id} in ${newEvent.zone_id}`);
        } else if (newEvent.severity === 'WARNING') {
          addToast('warning', `WARNING: ${newEvent.event_type}`, `Worker approaching buffer zone`);
        }
      }

      if (newEvent.safety_state) {
        setSafetyState(newEvent.safety_state);
      }
    });

    const unsubResync = liveSocket.onReconnectSync(() => {
      console.log('WebSocket reconnected — syncing missed events from SQLite...');
      addToast('info', 'WebSocket Reconnected', 'Synchronized live state from SQLite WAL');
      loadAlertsAndEvents();
      pollStatus();
    });

    liveSocket.connect();

    return () => {
      clearInterval(pollInterval);
      unsubState();
      unsubEvent();
      unsubResync();
      liveSocket.disconnect();
    };
  }, [pollStatus, loadAlertsAndEvents, addToast]);

  // Operator Handlers
  const handleTogglePlay = useCallback(async () => {
    try {
      if (streamStatus?.is_running) {
        await stopDemoPipeline();
        addToast('info', 'Stream Paused', 'Demo pipeline paused');
      } else {
        await startDemoPipeline();
        addToast('success', 'Stream Resumed', 'Demo pipeline running');
      }
      pollStatus();
    } catch (err) {
      console.error('Toggle play failed:', err);
      addToast('error', 'Playback Error', 'Failed to toggle stream state');
    }
  }, [streamStatus?.is_running, addToast, pollStatus]);

  const handleRestart = useCallback(async () => {
    try {
      await restartDemoPipeline();
      addToast('info', 'Stream Restarted', 'Replay restarted cleanly from frame 0');
      pollStatus();
      loadAlertsAndEvents();
    } catch (err) {
      console.error('Restart failed:', err);
      addToast('error', 'Restart Error', 'Failed to restart pipeline');
    }
  }, [addToast, pollStatus, loadAlertsAndEvents]);

  const handleSeek = useCallback(async (frame: number) => {
    try {
      const res = await seekDemoPipeline(frame);
      setStreamStatus((prev) => prev ? {
        ...prev,
        current_frame_id: res.frame,
        safety_state: res.safety_state || prev.safety_state,
        is_running: res.is_running !== undefined ? res.is_running : prev.is_running
      } : null);
      if (res.safety_state) {
        setSafetyState(res.safety_state);
      }
      return res;
    } catch (err) {
      console.error('Seek failed in App handler:', err);
      throw err;
    }
  }, []);

  // Global Keyboard Shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement | null;
      const isInput =
        target && (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || (target as any).isContentEditable);

      if (e.key === 'Escape') {
        if (selectedEvent) {
          setSelectedEvent(null);
          return;
        }
        if (actionModal.type) {
          setActionModal({ type: null, eventId: null });
          return;
        }
        if (shortcutsModalOpen) {
          setShortcutsModalOpen(false);
          return;
        }
      }

      if (isInput) return;

      if (e.key === '?' || (e.shiftKey && e.key === '/')) {
        e.preventDefault();
        setShortcutsModalOpen((prev) => !prev);
      } else if (e.key === ' ' || e.code === 'Space') {
        e.preventDefault();
        handleTogglePlay();
      } else if (e.key === 'r' || e.key === 'R') {
        e.preventDefault();
        handleRestart();
      } else if (e.key >= '1' && e.key <= '9') {
        const pageMap: Record<string, PageId> = {
          '1': 'command-center',
          '2': 'monitoring',
          '3': 'cameras',
          '4': 'alerts',
          '5': 'history',
          '6': 'analytics',
          '7': 'health',
          '8': 'replay',
          '9': 'reports'
        };
        if (pageMap[e.key]) {
          e.preventDefault();
          navigateTo(pageMap[e.key]);
        }
      } else if (e.key === '0') {
        e.preventDefault();
        navigateTo('settings');
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [selectedEvent, actionModal.type, shortcutsModalOpen, handleTogglePlay, handleRestart, navigateTo]);

  const handleOpenAcknowledge = (eventId: string) => {
    setActionModal({ type: 'acknowledge', eventId });
  };

  const handleOpenResolve = (eventId: string) => {
    setActionModal({ type: 'resolve', eventId });
  };

  const handleActionSubmit = async (eventId: string, operator: string, note: string) => {
    if (actionModal.type === 'acknowledge') {
      await acknowledgeEvent(eventId, operator, note);
      addToast('success', 'Alert Acknowledged', `Event ${eventId} acknowledged by ${operator}`);
    } else if (actionModal.type === 'resolve') {
      await resolveEvent(eventId, operator, note);
      addToast('success', 'Incident Resolved', `Event ${eventId} cleared and resolved`);
    }
    await loadAlertsAndEvents();
    setActionModal({ type: null, eventId: null });
  };

  const isUnknown = safetyState === 'UNKNOWN' || cameraHealth?.health_state === 'UNKNOWN';
  const criticalAlertCount = activeAlerts.filter((a) => a.severity === 'CRITICAL').length;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', backgroundColor: 'var(--bg-app, #090b10)', overflow: 'hidden' }}>
      {/* 1. Mandatory Regulatory Safety Disclaimer Banner */}
      <SafetyBoundaryBanner />

      {/* 2. Main Application Body with Persistent Sidebar & Workspace */}
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        {/* Left Persistent Sidebar */}
        <Sidebar
          currentPage={currentPage}
          onSelectPage={navigateTo}
          activeAlertCount={activeAlerts.length}
          criticalAlertCount={criticalAlertCount}
          systemStatus={systemHealth?.status || 'READY'}
          safetyState={safetyState}
        />

        {/* Right Content Area */}
        <div style={{ display: 'flex', flexDirection: 'column', flex: 1, overflow: 'hidden' }}>
          {/* Topbar Header */}
          <Topbar
            safetyState={safetyState}
            connectionState={connectionState}
            activeAlertCount={activeAlerts.length}
            onOpenAlerts={() => navigateTo('alerts')}
            onOpenShortcuts={() => setShortcutsModalOpen(true)}
            systemStatus={systemHealth?.status || 'READY'}
          />

          {/* High-visibility Critical Unknown Warning Bar */}
          {isUnknown && (
            <div className="system-unknown-alert-bar">
              <AlertTriangle size={22} color="#f43f5e" />
              <span>
                SYSTEM UNKNOWN: CAMERA / SENSOR DATA UNAVAILABLE — OPERATING IN CONSERVATIVE FAIL-SAFE MODE. PHYSICAL INSPECTION REQUIRED.
              </span>
            </div>
          )}

          {/* Scrollable Page Body */}
          <main style={{ flex: 1, overflowY: 'auto', backgroundColor: 'var(--bg-app, #090b10)' }}>
            {currentPage === 'command-center' && (
              <CommandCenterPage
                streamStatus={streamStatus}
                systemHealth={systemHealth}
                cameraHealth={cameraHealth}
                activeAlerts={activeAlerts}
                recentEvents={events}
                safetyState={safetyState}
                onTogglePlay={handleTogglePlay}
                onSelectEvent={(evt) => setSelectedEvent(evt)}
                onOpenAcknowledge={handleOpenAcknowledge}
                onOpenResolve={handleOpenResolve}
                onNavigate={navigateTo}
              />
            )}

            {currentPage === 'worker-safety' && (
              <WorkerSafetyPage onNavigate={navigateTo} />
            )}

            {currentPage === 'monitoring' && (
              <LiveMonitoringPage
                streamStatus={streamStatus}
                cameraHealth={cameraHealth}
                safetyState={safetyState}
                liveEvents={liveWebSocketEvents}
                onTogglePlay={handleTogglePlay}
                onRestart={handleRestart}
                onSelectEvent={(evt) => setSelectedEvent(evt)}
              />
            )}

            {currentPage === 'cameras' && (
              <CamerasPage
                cameraHealth={cameraHealth}
                streamStatus={streamStatus}
                safetyState={safetyState}
                onNavigate={navigateTo}
              />
            )}

            {currentPage === 'alerts' && (
              <AlertsPage
                events={events}
                activeAlerts={activeAlerts}
                onSelectEvent={(evt) => setSelectedEvent(evt)}
                onOpenAcknowledge={handleOpenAcknowledge}
                onOpenResolve={handleOpenResolve}
                onRefresh={loadAlertsAndEvents}
              />
            )}

            {currentPage === 'history' && (
              <EventHistoryPage
                events={events}
                onSelectEvent={(evt) => setSelectedEvent(evt)}
              />
            )}

            {currentPage === 'analytics' && (
              <AnalyticsPage events={events} />
            )}

            {currentPage === 'health' && (
              <SystemHealthPage
                systemHealth={systemHealth}
                cameraHealth={cameraHealth}
                streamStatus={streamStatus}
              />
            )}

            {currentPage === 'replay' && (
              <ReplayScenariosPage
                streamStatus={streamStatus}
                safetyState={safetyState}
                onTogglePlay={handleTogglePlay}
                onRestart={handleRestart}
                onSeek={handleSeek}
              />
            )}

            {currentPage === 'reports' && (
              <ReportsPage />
            )}

            {currentPage === 'settings' && (
              <SettingsPage />
            )}
          </main>
        </div>
      </div>

      {/* Global Modals */}
      {selectedEvent && (
        <EventDetailModal
          event={selectedEvent}
          onClose={() => setSelectedEvent(null)}
          onAcknowledge={handleOpenAcknowledge}
          onResolve={handleOpenResolve}
        />
      )}

      {actionModal.type && (
        <ActionModal
          type={actionModal.type}
          eventId={actionModal.eventId}
          onClose={() => setActionModal({ type: null, eventId: null })}
          onSubmit={handleActionSubmit}
        />
      )}

      {shortcutsModalOpen && (
        <KeyboardShortcutsModal onClose={() => setShortcutsModalOpen(false)} />
      )}

      {/* Non-intrusive Toast Notifications */}
      <ToastContainer toasts={toasts} onDismiss={dismissToast} />
    </div>
  );
};

export default App;
