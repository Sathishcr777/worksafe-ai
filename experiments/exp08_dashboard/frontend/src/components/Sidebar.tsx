import React, { useState } from 'react';
import {
  LayoutDashboard,
  Video,
  Camera,
  AlertTriangle,
  History,
  BarChart3,
  Activity,
  PlayCircle,
  FileText,
  Settings,
  Shield,
  ChevronLeft,
  ChevronRight,
  Users
} from 'lucide-react';
import type { SafetyState } from '../types';

export type PageId =
  | 'command-center'
  | 'worker-safety'
  | 'monitoring'
  | 'cameras'
  | 'alerts'
  | 'history'
  | 'analytics'
  | 'health'
  | 'replay'
  | 'reports'
  | 'settings';

interface SidebarProps {
  currentPage: PageId;
  onSelectPage: (page: PageId) => void;
  activeAlertCount: number;
  criticalAlertCount: number;
  systemStatus: 'READY' | 'DEGRADED' | 'UNKNOWN';
  safetyState: SafetyState;
  isWsConnected?: boolean;
  isDbConnected?: boolean;
  isPipelineRunning?: boolean;
  isEngineRunning?: boolean;
}

interface NavItem {
  id: PageId;
  label: string;
  icon: React.ReactNode;
  badge?: number;
  badgeColor?: string;
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentPage,
  onSelectPage,
  activeAlertCount,
  criticalAlertCount,
  isWsConnected = true,
  isDbConnected = true,
  isPipelineRunning = true,
  isEngineRunning = true
}) => {
  const [collapsed, setCollapsed] = useState(false);

  // 1. COMMAND GROUP
  const commandNav: NavItem[] = [
    { id: 'command-center', label: 'Command Center', icon: <LayoutDashboard size={17} /> },
    { id: 'worker-safety', label: 'Worker Safety', icon: <Users size={17} /> },
    { id: 'monitoring', label: 'Live Monitoring', icon: <Video size={17} /> }
  ];

  // 2. OPERATIONS GROUP
  const opsNav: NavItem[] = [
    { id: 'cameras', label: 'Cameras', icon: <Camera size={17} /> },
    {
      id: 'alerts',
      label: 'Safety Alert Center',
      icon: <AlertTriangle size={17} />,
      badge: activeAlertCount > 0 ? activeAlertCount : undefined,
      badgeColor: criticalAlertCount > 0 ? '#ef4444' : '#f59e0b'
    },
    { id: 'history', label: 'Event History', icon: <History size={17} /> },
    { id: 'replay', label: 'Safety Scenario Lab', icon: <PlayCircle size={17} /> }
  ];

  // 3. INTELLIGENCE GROUP
  const intelNav: NavItem[] = [
    { id: 'analytics', label: 'Analytics', icon: <BarChart3 size={17} /> },
    { id: 'health', label: 'System Health', icon: <Activity size={17} /> },
    { id: 'reports', label: 'Reports', icon: <FileText size={17} /> }
  ];

  // 4. SYSTEM GROUP
  const systemNav: NavItem[] = [
    { id: 'settings', label: 'Settings', icon: <Settings size={17} /> }
  ];

  const renderNavSection = (title: string, items: NavItem[]) => (
    <div style={{ marginBottom: '10px' }}>
      {!collapsed && (
        <div
          style={{
            fontSize: '0.625rem',
            fontWeight: 700,
            letterSpacing: '0.08em',
            color: '#475569',
            padding: '6px 12px 4px 12px',
            textTransform: 'uppercase'
          }}
        >
          {title}
        </div>
      )}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
        {items.map((item) => {
          const isActive = currentPage === item.id;
          return (
            <button
              key={item.id}
              onClick={() => onSelectPage(item.id)}
              title={collapsed ? `${item.label}${item.badge ? ` (${item.badge})` : ''}` : undefined}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: collapsed ? 'center' : 'space-between',
                padding: collapsed ? '10px 0' : '8px 12px',
                borderRadius: '4px',
                backgroundColor: isActive ? 'rgba(14, 165, 233, 0.14)' : 'transparent',
                border: isActive ? '1px solid #0284c7' : '1px solid transparent',
                color: isActive ? '#38bdf8' : '#94a3b8',
                cursor: 'pointer',
                fontSize: '0.75rem',
                fontWeight: isActive ? 600 : 500,
                letterSpacing: '0.03em',
                transition: 'all 0.15s ease',
                textAlign: 'left',
                position: 'relative'
              }}
              onMouseEnter={(e) => {
                if (!isActive) {
                  (e.currentTarget as HTMLElement).style.backgroundColor = '#111726';
                  (e.currentTarget as HTMLElement).style.color = '#f1f5f9';
                }
              }}
              onMouseLeave={(e) => {
                if (!isActive) {
                  (e.currentTarget as HTMLElement).style.backgroundColor = 'transparent';
                  (e.currentTarget as HTMLElement).style.color = '#94a3b8';
                }
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <span style={{ color: isActive ? '#38bdf8' : '#64748b', display: 'flex', alignItems: 'center' }}>
                  {item.icon}
                </span>
                {!collapsed && <span>{item.label}</span>}
              </div>

              {/* Badge */}
              {item.badge !== undefined && item.badge > 0 && (
                <span
                  style={{
                    position: collapsed ? 'absolute' : 'static',
                    top: collapsed ? '4px' : undefined,
                    right: collapsed ? '6px' : undefined,
                    fontFamily: 'var(--font-mono, monospace)',
                    fontSize: '0.625rem',
                    fontWeight: 700,
                    padding: '1px 5px',
                    borderRadius: '10px',
                    backgroundColor: item.badgeColor || '#ef4444',
                    color: '#ffffff',
                    lineHeight: 1.2
                  }}
                >
                  {item.badge}
                </span>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );

  return (
    <aside
      style={{
        width: collapsed ? '64px' : '235px',
        minWidth: collapsed ? '64px' : '235px',
        backgroundColor: '#070a10',
        borderRight: '1px solid #161e2e',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        userSelect: 'none',
        height: '100%',
        zIndex: 10,
        transition: 'width 0.2s ease, min-width 0.2s ease'
      }}
    >
      {/* Top Header & Navigation */}
      <div style={{ display: 'flex', flexDirection: 'column', overflowY: 'auto' }}>
        {/* Brand Header */}
        <div
          style={{
            padding: collapsed ? '14px 10px' : '14px 16px',
            borderBottom: '1px solid #161e2e',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div
              style={{
                width: '32px',
                height: '32px',
                borderRadius: '4px',
                backgroundColor: 'rgba(16, 185, 129, 0.12)',
                border: '1px solid #059669',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#10b981',
                flexShrink: 0
              }}
            >
              <Shield size={18} />
            </div>
            {!collapsed && (
              <div>
                <div
                  style={{
                    fontSize: '0.875rem',
                    fontWeight: 700,
                    letterSpacing: '0.06em',
                    color: '#f8fafc',
                    lineHeight: 1.1
                  }}
                >
                  WORKSAFE AI
                </div>
                <div
                  style={{
                    fontSize: '0.625rem',
                    color: '#64748b',
                    letterSpacing: '0.04em',
                    textTransform: 'uppercase',
                    marginTop: '2px'
                  }}
                >
                  Safety Operations
                </div>
              </div>
            )}
          </div>

          {/* Collapse/Expand Toggle */}
          <button
            onClick={() => setCollapsed(!collapsed)}
            title={collapsed ? 'Expand Sidebar' : 'Collapse Sidebar'}
            style={{
              background: 'none',
              border: '1px solid #1c2638',
              borderRadius: '4px',
              padding: '4px',
              color: '#64748b',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              backgroundColor: '#0b1019'
            }}
          >
            {collapsed ? <ChevronRight size={13} /> : <ChevronLeft size={13} />}
          </button>
        </div>

        {/* Navigation Groups */}
        <nav style={{ padding: collapsed ? '10px 6px' : '12px 8px' }}>
          {renderNavSection('COMMAND', commandNav)}
          {renderNavSection('OPERATIONS', opsNav)}
          {renderNavSection('INTELLIGENCE', intelNav)}
          {renderNavSection('SYSTEM', systemNav)}
        </nav>
      </div>

      {/* Bottom: Facility & System Status Board */}
      <div
        style={{
          padding: collapsed ? '10px 6px' : '12px 14px',
          borderTop: '1px solid #161e2e',
          backgroundColor: '#05070c',
          display: 'flex',
          flexDirection: 'column',
          gap: '8px'
        }}
      >
        {!collapsed ? (
          <>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div
                style={{
                  fontSize: '0.625rem',
                  fontWeight: 700,
                  letterSpacing: '0.08em',
                  color: '#64748b',
                  textTransform: 'uppercase'
                }}
              >
                FACILITY STATUS
              </div>
              <span
                style={{
                  fontSize: '0.625rem',
                  fontFamily: 'var(--font-mono, monospace)',
                  color: '#38bdf8',
                  fontWeight: 600
                }}
              >
                BAY 01
              </span>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '5px', fontSize: '0.6875rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#cbd5e1' }}>
                <span
                  style={{
                    width: '6px',
                    height: '6px',
                    borderRadius: '50%',
                    backgroundColor: isWsConnected ? '#10b981' : '#ef4444',
                    boxShadow: isWsConnected ? '0 0 6px #10b981' : 'none'
                  }}
                />
                <span>WebSocket {isWsConnected ? 'Live' : 'Reconnecting'}</span>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#cbd5e1' }}>
                <span
                  style={{
                    width: '6px',
                    height: '6px',
                    borderRadius: '50%',
                    backgroundColor: isDbConnected ? '#10b981' : '#f59e0b',
                    boxShadow: isDbConnected ? '0 0 6px #10b981' : 'none'
                  }}
                />
                <span>SQLite WAL Persistent</span>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#cbd5e1' }}>
                <span
                  style={{
                    width: '6px',
                    height: '6px',
                    borderRadius: '50%',
                    backgroundColor: isPipelineRunning ? '#10b981' : '#ef4444',
                    boxShadow: isPipelineRunning ? '0 0 6px #10b981' : 'none'
                  }}
                />
                <span>Vision Pipeline Online</span>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#cbd5e1' }}>
                <span
                  style={{
                    width: '6px',
                    height: '6px',
                    borderRadius: '50%',
                    backgroundColor: isEngineRunning ? '#10b981' : '#ef4444',
                    boxShadow: isEngineRunning ? '0 0 6px #10b981' : 'none'
                  }}
                />
                <span>Event Engine Nominal</span>
              </div>
            </div>

            <div
              style={{
                fontSize: '0.625rem',
                fontFamily: 'var(--font-mono, monospace)',
                color: '#475569',
                marginTop: '4px',
                borderTop: '1px solid #141a27',
                paddingTop: '6px',
                display: 'flex',
                justifyContent: 'space-between'
              }}
            >
              <span>WorkSafe AI</span>
              <span>v1.0.0</span>
            </div>
          </>
        ) : (
          <div
            title="System Status: All Services Nominal"
            style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '6px' }}
          >
            <span
              style={{
                width: '8px',
                height: '8px',
                borderRadius: '50%',
                backgroundColor: isWsConnected && isPipelineRunning ? '#10b981' : '#ef4444',
                boxShadow: isWsConnected && isPipelineRunning ? '0 0 6px #10b981' : 'none'
              }}
            />
          </div>
        )}
      </div>
    </aside>
  );
};
