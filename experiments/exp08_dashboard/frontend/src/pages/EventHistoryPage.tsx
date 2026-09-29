import React, { useState, useMemo } from 'react';
import {
  Search,
  Download,
  ChevronLeft,
  ChevronRight,
  Eye,
  FileText
} from 'lucide-react';
import { SeverityBadge } from '../components/SeverityBadge';
import { StatusBadge } from '../components/StatusBadge';
import { EmptyState } from '../components/EmptyState';
import type { SafetyEvent } from '../types';

interface EventHistoryPageProps {
  events: SafetyEvent[];
  onSelectEvent: (event: SafetyEvent) => void;
}

export const EventHistoryPage: React.FC<EventHistoryPageProps> = ({ events, onSelectEvent }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [severityFilter, setSeverityFilter] = useState('ALL');
  const [stateFilter, setStateFilter] = useState('ALL');
  const [eventTypeFilter, setEventTypeFilter] = useState('ALL');
  const [cameraFilter, setCameraFilter] = useState('ALL');
  const [page, setPage] = useState(1);
  const pageSize = 20;

  const filteredEvents = useMemo(() => {
    return events.filter((e) => {
      if (severityFilter !== 'ALL' && e.severity !== severityFilter) return false;
      if (stateFilter !== 'ALL' && e.safety_state !== stateFilter) return false;
      if (eventTypeFilter !== 'ALL' && e.event_type !== eventTypeFilter) return false;
      if (cameraFilter !== 'ALL' && e.camera_id !== cameraFilter) return false;

      if (searchTerm.trim()) {
        const q = searchTerm.toLowerCase();
        const matchId = e.event_id.toLowerCase().includes(q);
        const matchType = e.event_type.toLowerCase().includes(q);
        const matchZone = (e.zone_id || '').toLowerCase().includes(q);
        const matchTrack = e.track_id ? String(e.track_id).includes(q) : false;
        if (!matchId && !matchType && !matchZone && !matchTrack) return false;
      }

      return true;
    });
  }, [events, severityFilter, stateFilter, eventTypeFilter, cameraFilter, searchTerm]);

  const totalPages = Math.ceil(filteredEvents.length / pageSize) || 1;
  const paginatedEvents = filteredEvents.slice((page - 1) * pageSize, page * pageSize);

  const formatTime = (ts?: number | null) => {
    if (!ts) return 'N/A';
    const d = new Date(ts > 1e11 ? ts : ts * 1000);
    return `${d.toLocaleDateString()} ${d.toLocaleTimeString()}.${String(d.getMilliseconds()).padStart(3, '0')}`;
  };

  const handleExportJSON = () => {
    const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(filteredEvents, null, 2));
    const a = document.createElement('a');
    a.setAttribute('href', dataStr);
    a.setAttribute('download', `worksafe_audit_log_${Date.now()}.json`);
    document.body.appendChild(a);
    a.click();
    a.remove();
  };

  const handleExportCSV = () => {
    const headers = ['event_id', 'timestamp', 'severity', 'safety_state', 'event_type', 'camera_id', 'zone_id', 'track_id', 'lifecycle_status'];
    const rows = filteredEvents.map((e) => [
      e.event_id,
      e.timestamp,
      e.severity,
      e.safety_state,
      e.event_type,
      e.camera_id,
      e.zone_id || '',
      e.track_id || '',
      e.lifecycle_status
    ]);
    const csvContent = 'data:text/csv;charset=utf-8,' + [headers.join(','), ...rows.map((r) => r.join(','))].join('\n');
    const a = document.createElement('a');
    a.setAttribute('href', encodeURI(csvContent));
    a.setAttribute('download', `worksafe_audit_log_${Date.now()}.csv`);
    document.body.appendChild(a);
    a.click();
    a.remove();
  };

  return (
    <div style={{ padding: '20px 24px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
      {/* Control Bar: Filters & Export */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '12px',
          backgroundColor: 'var(--bg-card, #11151f)',
          border: '1px solid var(--border-dim, #1f2738)',
          borderRadius: '6px',
          padding: '12px 16px'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
          {/* Search Box */}
          <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
            <Search size={14} style={{ position: 'absolute', left: '10px', color: 'var(--text-muted, #64748b)' }} />
            <input
              type="text"
              placeholder="Search historical events..."
              value={searchTerm}
              onChange={(e) => {
                setSearchTerm(e.target.value);
                setPage(1);
              }}
              style={{
                padding: '6px 12px 6px 30px',
                borderRadius: '4px',
                backgroundColor: 'var(--bg-app, #090b10)',
                border: '1px solid var(--border-mid, #2d374d)',
                color: 'var(--text-primary, #f1f5f9)',
                fontSize: '0.75rem',
                fontFamily: 'inherit',
                outline: 'none',
                width: '220px'
              }}
            />
          </div>

          {/* Severity Dropdown */}
          <select
            value={severityFilter}
            onChange={(e) => {
              setSeverityFilter(e.target.value);
              setPage(1);
            }}
            style={{
              padding: '6px 10px',
              borderRadius: '4px',
              backgroundColor: 'var(--bg-app, #090b10)',
              border: '1px solid var(--border-mid, #2d374d)',
              color: 'var(--text-primary, #f1f5f9)',
              fontSize: '0.75rem',
              outline: 'none',
              cursor: 'pointer'
            }}
          >
            <option value="ALL">All Severities</option>
            <option value="CRITICAL">Critical</option>
            <option value="WARNING">Warning</option>
            <option value="SYSTEM">System</option>
            <option value="INFO">Info</option>
          </select>

          {/* State Dropdown */}
          <select
            value={stateFilter}
            onChange={(e) => {
              setStateFilter(e.target.value);
              setPage(1);
            }}
            style={{
              padding: '6px 10px',
              borderRadius: '4px',
              backgroundColor: 'var(--bg-app, #090b10)',
              border: '1px solid var(--border-mid, #2d374d)',
              color: 'var(--text-primary, #f1f5f9)',
              fontSize: '0.75rem',
              outline: 'none',
              cursor: 'pointer'
            }}
          >
            <option value="ALL">All States</option>
            <option value="NORMAL">Normal</option>
            <option value="WARNING">Warning</option>
            <option value="DANGER">Danger</option>
            <option value="RECOVERY">Recovery</option>
          </select>

          {/* Event Type Dropdown */}
          <select
            value={eventTypeFilter}
            onChange={(e) => {
              setEventTypeFilter(e.target.value);
              setPage(1);
            }}
            style={{
              padding: '6px 10px',
              borderRadius: '4px',
              backgroundColor: 'var(--bg-app, #090b10)',
              border: '1px solid var(--border-mid, #2d374d)',
              color: 'var(--text-primary, #f1f5f9)',
              fontSize: '0.75rem',
              outline: 'none',
              cursor: 'pointer'
            }}
          >
            <option value="ALL">All Event Types</option>
            <option value="DANGER_ENTERED">Danger Entered</option>
            <option value="WARNING_ENTERED">Warning Entered</option>
            <option value="RECOVERY_ENTERED">Recovery Entered</option>
            <option value="NORMAL_ENTERED">Normal Entered</option>
          </select>

          {/* Camera Filter Dropdown */}
          <select
            value={cameraFilter}
            onChange={(e) => {
              setCameraFilter(e.target.value);
              setPage(1);
            }}
            style={{
              padding: '6px 10px',
              borderRadius: '4px',
              backgroundColor: 'var(--bg-app, #090b10)',
              border: '1px solid var(--border-mid, #2d374d)',
              color: 'var(--text-primary, #f1f5f9)',
              fontSize: '0.75rem',
              outline: 'none',
              cursor: 'pointer'
            }}
          >
            <option value="ALL">All Cameras</option>
            <option value="cam_bay_01">CAM-BAY-01</option>
            <option value="cam_bay_02">CAM-BAY-02</option>
            <option value="cam_bay_03">CAM-BAY-03</option>
            <option value="cam_bay_04">CAM-BAY-04</option>
          </select>
        </div>

        {/* Export Buttons */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <button
            onClick={handleExportCSV}
            style={{
              padding: '6px 12px',
              borderRadius: '4px',
              backgroundColor: 'var(--bg-app, #090b10)',
              border: '1px solid var(--border-mid, #2d374d)',
              color: 'var(--text-secondary, #94a3b8)',
              fontSize: '0.75rem',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px'
            }}
          >
            <Download size={13} />
            <span>Export CSV</span>
          </button>

          <button
            onClick={handleExportJSON}
            style={{
              padding: '6px 12px',
              borderRadius: '4px',
              backgroundColor: 'var(--bg-app, #090b10)',
              border: '1px solid var(--border-mid, #2d374d)',
              color: 'var(--text-secondary, #94a3b8)',
              fontSize: '0.75rem',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px'
            }}
          >
            <FileText size={13} />
            <span>Export JSON</span>
          </button>
        </div>
      </div>

      {/* Historical Audit Table */}
      <div
        style={{
          backgroundColor: 'var(--bg-card, #11151f)',
          border: '1px solid var(--border-dim, #1f2738)',
          borderRadius: '6px',
          overflow: 'hidden'
        }}
      >
        {filteredEvents.length === 0 ? (
          <EmptyState
            title="Zero Historical Events Match"
            description="No safety audit events match your selected criteria. Try resetting filters or broadening search parameters."
            icon="search"
          />
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.75rem' }}>
              <thead>
                <tr
                  style={{
                    backgroundColor: 'var(--bg-card-subtle, #161c2b)',
                    borderBottom: '1px solid var(--border-dim, #1f2738)',
                    color: 'var(--text-muted, #64748b)',
                    fontWeight: 600,
                    textTransform: 'uppercase',
                    letterSpacing: '0.05em'
                  }}
                >
                  <th style={{ padding: '12px 16px' }}>Timestamp</th>
                  <th style={{ padding: '12px 16px' }}>Event ID</th>
                  <th style={{ padding: '12px 16px' }}>Type</th>
                  <th style={{ padding: '12px 16px' }}>Severity</th>
                  <th style={{ padding: '12px 16px' }}>State</th>
                  <th style={{ padding: '12px 16px' }}>Zone</th>
                  <th style={{ padding: '12px 16px' }}>Track ID</th>
                  <th style={{ padding: '12px 16px' }}>Status</th>
                  <th style={{ padding: '12px 16px', textAlign: 'right' }}>View</th>
                </tr>
              </thead>
              <tbody>
                {paginatedEvents.map((evt) => (
                  <tr
                    key={evt.event_id}
                    onClick={() => onSelectEvent(evt)}
                    style={{
                      borderBottom: '1px solid var(--border-dim, #1f2738)',
                      cursor: 'pointer',
                      transition: 'background-color 0.1s'
                    }}
                    onMouseEnter={(e) => {
                      (e.currentTarget as HTMLElement).style.backgroundColor = 'var(--bg-card-hover, #1c2336)';
                    }}
                    onMouseLeave={(e) => {
                      (e.currentTarget as HTMLElement).style.backgroundColor = 'transparent';
                    }}
                  >
                    <td style={{ padding: '12px 16px', fontFamily: 'var(--font-mono, monospace)', color: 'var(--text-secondary, #94a3b8)', whiteSpace: 'nowrap' }}>
                      {formatTime(evt.timestamp)}
                    </td>
                    <td style={{ padding: '12px 16px', fontFamily: 'var(--font-mono, monospace)', color: 'var(--text-primary, #f1f5f9)', fontWeight: 600 }}>
                      {evt.event_id}
                    </td>
                    <td style={{ padding: '12px 16px', color: 'var(--text-primary, #f1f5f9)' }}>
                      {evt.event_type.replace(/_/g, ' ')}
                    </td>
                    <td style={{ padding: '12px 16px' }}>
                      <SeverityBadge severity={evt.severity} size="sm" />
                    </td>
                    <td style={{ padding: '12px 16px' }}>
                      <StatusBadge state={evt.safety_state} size="sm" />
                    </td>
                    <td style={{ padding: '12px 16px', color: 'var(--text-secondary, #94a3b8)' }}>
                      {evt.zone_id || 'Aisle'}
                    </td>
                    <td style={{ padding: '12px 16px', fontFamily: 'var(--font-mono, monospace)', color: '#38bdf8' }}>
                      {evt.track_id ? `#${evt.track_id}` : '—'}
                    </td>
                    <td style={{ padding: '12px 16px' }}>
                      <span style={{ fontFamily: 'var(--font-mono, monospace)', fontSize: '0.6875rem', color: 'var(--text-muted, #64748b)' }}>
                        {evt.lifecycle_status}
                      </span>
                    </td>
                    <td style={{ padding: '12px 16px', textAlign: 'right' }}>
                      <button
                        onClick={() => onSelectEvent(evt)}
                        style={{
                          background: 'none',
                          border: 'none',
                          color: '#38bdf8',
                          cursor: 'pointer',
                          padding: '4px'
                        }}
                      >
                        <Eye size={14} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination Bar */}
        {filteredEvents.length > 0 && (
          <div
            style={{
              padding: '12px 16px',
              borderTop: '1px solid var(--border-dim, #1f2738)',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              backgroundColor: 'var(--bg-card-subtle, #161c2b)',
              fontSize: '0.75rem',
              color: 'var(--text-secondary, #94a3b8)'
            }}
          >
            <span>
              Showing {Math.min((page - 1) * pageSize + 1, filteredEvents.length)}–
              {Math.min(page * pageSize, filteredEvents.length)} of {filteredEvents.length} records (SQLite WAL Journal)
            </span>

            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <button
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                style={{
                  padding: '4px 8px',
                  borderRadius: '4px',
                  backgroundColor: 'var(--bg-app, #090b10)',
                  border: '1px solid var(--border-mid, #2d374d)',
                  color: page <= 1 ? 'var(--text-muted, #64748b)' : 'var(--text-primary, #f1f5f9)',
                  cursor: page <= 1 ? 'not-allowed' : 'pointer'
                }}
              >
                <ChevronLeft size={14} />
              </button>

              <span style={{ fontFamily: 'var(--font-mono, monospace)' }}>
                Page {page} / {totalPages}
              </span>

              <button
                disabled={page >= totalPages}
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                style={{
                  padding: '4px 8px',
                  borderRadius: '4px',
                  backgroundColor: 'var(--bg-app, #090b10)',
                  border: '1px solid var(--border-mid, #2d374d)',
                  color: page >= totalPages ? 'var(--text-muted, #64748b)' : 'var(--text-primary, #f1f5f9)',
                  cursor: page >= totalPages ? 'not-allowed' : 'pointer'
                }}
              >
                <ChevronRight size={14} />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
