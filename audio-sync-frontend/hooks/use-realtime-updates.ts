import { useEffect, useRef, useState, useCallback } from 'react';
import { getWebSocketClient, WebSocketMessage } from '@/lib/websocket-client';

interface UseRealtimeUpdatesOptions {
  enabled?: boolean;
  token?: string;
}

export function useRealtimeUpdates(options: UseRealtimeUpdatesOptions = {}) {
  const { enabled = true, token } = options;
  const wsClientRef = useRef<ReturnType<typeof getWebSocketClient> | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [syncProgress, setSyncProgress] = useState<Record<string, unknown> | null>(null);
  const [downloadProgress, setDownloadProgress] = useState<Record<string, unknown> | null>(null);

  useEffect(() => {
    if (!enabled || !token) return;

    try {
      wsClientRef.current = getWebSocketClient(token);

      // Setup event handlers
      const unsubscribeConnected = wsClientRef.current.on('connected', () => {
        setIsConnected(true);
      });

      const unsubscribeDisconnected = wsClientRef.current.on('disconnected', () => {
        setIsConnected(false);
      });

      const unsubscribeSyncProgress = wsClientRef.current.on(
        'sync.progress',
        (message: WebSocketMessage) => {
          setSyncProgress({
            type: 'sync.progress',
            ...(message as Record<string, unknown>),
          });
        }
      );

      const unsubscribeSyncCompleted = wsClientRef.current.on(
        'sync.completed',
        (message: WebSocketMessage) => {
          setSyncProgress({
            type: 'sync.completed',
            ...(message as Record<string, unknown>),
          });
        }
      );

      const unsubscribeSyncFailed = wsClientRef.current.on(
        'sync.failed',
        (message: WebSocketMessage) => {
          setSyncProgress({
            type: 'sync.failed',
            ...(message as Record<string, unknown>),
          });
        }
      );

      const unsubscribeDownloadProgress = wsClientRef.current.on(
        'download.progress',
        (message: WebSocketMessage) => {
          setDownloadProgress(message as Record<string, unknown>);
        }
      );

      // Connect to WebSocket
      wsClientRef.current.connect();

      // Cleanup on unmount
      return () => {
        unsubscribeConnected();
        unsubscribeDisconnected();
        unsubscribeSyncProgress();
        unsubscribeSyncCompleted();
        unsubscribeSyncFailed();
        unsubscribeDownloadProgress();
      };
    } catch (error) {
      console.error('Failed to initialize WebSocket client:', error);
    }
  }, [enabled, token]);

  const on = useCallback((event: string, callback: (message: WebSocketMessage) => void) => {
    if (!wsClientRef.current) return () => {};
    return wsClientRef.current.on(event, callback);
  }, []);

  const send = useCallback((message: WebSocketMessage) => {
    if (wsClientRef.current) {
      wsClientRef.current.send(message);
    }
  }, []);

  const disconnect = useCallback(() => {
    if (wsClientRef.current) {
      wsClientRef.current.disconnect();
      wsClientRef.current = null;
    }
  }, []);

  return {
    isConnected,
    syncProgress,
    downloadProgress,
    on,
    send,
    disconnect,
  };
}
