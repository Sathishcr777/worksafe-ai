/**
 * WorkSafe AI — Resilient WebSocket Client (Experiment 08).
 * 
 * Manages live WebSocket event stream with:
 * - Bounded exponential backoff reconnection (1s -> 2s -> 4s -> max 15s)
 * - Explicit connection lifecycle state reporting (CONNECTED, RECONNECTING, DISCONNECTED)
 * - Automatic missed-event resynchronization callback on reconnect
 */

import type { SafetyEvent } from '../types';

export type ConnectionState = 'CONNECTED' | 'CONNECTING' | 'RECONNECTING' | 'DISCONNECTED';

export type EventCallback = (event: SafetyEvent) => void;
export type StateCallback = (state: ConnectionState) => void;
export type ReconnectSyncCallback = () => void;

export class ResilientWebSocket {
  private url: string;
  private ws: WebSocket | null = null;
  private isIntentionallyClosed: boolean = false;
  private reconnectAttempt: number = 0;
  private maxReconnectDelayMs: number = 15000;
  private baseReconnectDelayMs: number = 1000;
  private reconnectTimer: any = null;
  private hadPriorConnection: boolean = false;

  private eventListeners: Set<EventCallback> = new Set();
  private stateListeners: Set<StateCallback> = new Set();
  private reconnectSyncListeners: Set<ReconnectSyncCallback> = new Set();

  public currentState: ConnectionState = 'DISCONNECTED';

  constructor(url?: string) {
    if (url) {
      this.url = url;
    } else {
      const loc = window.location;
      const protocol = loc.protocol === 'https:' ? 'wss:' : 'ws:';
      this.url = `${protocol}//${loc.host}/ws/events`;
    }
  }

  public connect(): void {
    this.isIntentionallyClosed = false;
    this.updateState(this.hadPriorConnection ? 'RECONNECTING' : 'CONNECTING');

    try {
      this.ws = new WebSocket(this.url);

      this.ws.onopen = () => {
        this.reconnectAttempt = 0;
        this.updateState('CONNECTED');

        if (this.hadPriorConnection) {
          // Trigger resync of missed events
          this.reconnectSyncListeners.forEach(cb => {
            try { cb(); } catch (err) { console.error('Error in resync callback:', err); }
          });
        }
        this.hadPriorConnection = true;
      };

      this.ws.onmessage = (event: MessageEvent) => {
        try {
          const raw = JSON.parse(event.data);
          const data = (raw.type === 'SAFETY_EVENT' && raw.data) ? raw.data : raw;
          // Broadcast to event subscribers
          this.eventListeners.forEach(cb => {
            try { cb(data as SafetyEvent); } catch (err) { console.error('Error in event listener:', err); }
          });
        } catch (err) {
          console.warn('Failed to parse WebSocket message:', event.data, err);
        }
      };

      this.ws.onclose = () => {
        if (!this.isIntentionallyClosed) {
          this.scheduleReconnect();
        } else {
          this.updateState('DISCONNECTED');
        }
      };

      this.ws.onerror = (err) => {
        console.warn('WebSocket encountered error:', err);
        // Onerror is generally followed by onclose
      };
    } catch (err) {
      console.error('Failed to create WebSocket:', err);
      this.scheduleReconnect();
    }
  }

  private scheduleReconnect(): void {
    this.updateState('RECONNECTING');
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);

    // Exponential backoff: min(base * 2^attempt, maxDelay)
    const delay = Math.min(
      this.baseReconnectDelayMs * Math.pow(2, this.reconnectAttempt),
      this.maxReconnectDelayMs
    );
    this.reconnectAttempt++;

    this.reconnectTimer = setTimeout(() => {
      this.connect();
    }, delay);
  }

  public disconnect(): void {
    this.isIntentionallyClosed = true;
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.updateState('DISCONNECTED');
  }

  private updateState(newState: ConnectionState): void {
    this.currentState = newState;
    this.stateListeners.forEach(cb => {
      try { cb(newState); } catch (err) { console.error('Error in state listener:', err); }
    });
  }

  public onEvent(callback: EventCallback): () => void {
    this.eventListeners.add(callback);
    return () => this.eventListeners.delete(callback);
  }

  public onStateChange(callback: StateCallback): () => void {
    this.stateListeners.add(callback);
    callback(this.currentState);
    return () => this.stateListeners.delete(callback);
  }

  public onReconnectSync(callback: ReconnectSyncCallback): () => void {
    this.reconnectSyncListeners.add(callback);
    return () => this.reconnectSyncListeners.delete(callback);
  }
}

export const liveSocket = new ResilientWebSocket();
