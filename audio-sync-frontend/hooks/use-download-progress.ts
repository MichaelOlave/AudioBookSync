import { useEffect, useState, useRef, useCallback } from 'react';
import { logger } from '@/lib/logger';

export interface DownloadProgressEvent {
  asin: string;
  filename: string;
  bytes_downloaded: number;
  total_bytes: number;
  progress_percent: number;
  speed_kbps: number;
  timestamp: number;
}

interface ProgressState {
  [asin: string]: DownloadProgressEvent;
}

export function useDownloadProgress() {
  const [progress, setProgress] = useState<ProgressState>({});
  const [isConnected, setIsConnected] = useState(false);
  const ws = useRef<WebSocket | null>(null);
  const reconnectTimeout = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttempts = useRef(0);
  const connectRef = useRef<() => void>(() => {});
  const MAX_RECONNECT_ATTEMPTS = 5;
  const RECONNECT_DELAY = 3000;

  const getWebSocketUrl = useCallback(() => {
    if (typeof window === 'undefined') return '';

    const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
    const wsUrl = baseUrl.replace('http://', 'ws://').replace('https://', 'wss://');
    const token = localStorage.getItem('accessToken');

    if (!token) {
      logger.warn('No access token available for WebSocket connection');
      return '';
    }

    const url = `${wsUrl}/ws/updates?token=${encodeURIComponent(token)}`;
    logger.debug('WebSocket URL configured', { url: url.replace(token, 'TOKEN_HIDDEN') });
    return url;
  }, []);

  const connect = useCallback(() => {
    const wsUrl = getWebSocketUrl();
    if (!wsUrl) {
      logger.warn('Cannot connect to WebSocket: missing URL');
      return;
    }

    try {
      logger.debug('Connecting to WebSocket...');
      ws.current = new WebSocket(wsUrl);

      ws.current.onopen = () => {
        logger.debug('WebSocket connected');
        setIsConnected(true);
        reconnectAttempts.current = 0;
      };

      ws.current.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          logger.debug('WebSocket message:', message.type);

          // Keep connection alive on any message
          setIsConnected(true);

          // Handle download.progress events
          if (message.type === 'download.progress' || message.type === 'download_progress') {
            const data = message.data;
            if (data.asin) {
              logger.debug(`Update progress for ${data.asin}: ${data.progress_percent}%`);
              setProgress((prev) => ({
                ...prev,
                [data.asin]: data,
              }));
            }
          }
        } catch (error) {
          logger.error('Failed to parse WebSocket message:', error);
        }
      };

      ws.current.onerror = (error) => {
        logger.error('WebSocket error:', error);
        setIsConnected(false);
      };

      ws.current.onclose = () => {
        logger.debug('WebSocket closed');
        setIsConnected(false);

        // Attempt to reconnect
        if (reconnectAttempts.current < MAX_RECONNECT_ATTEMPTS) {
          reconnectAttempts.current += 1;
          logger.debug(`Attempting to reconnect (${reconnectAttempts.current}/${MAX_RECONNECT_ATTEMPTS})...`);

          reconnectTimeout.current = setTimeout(() => {
            connectRef.current();
          }, RECONNECT_DELAY);
        } else {
          logger.error('Max reconnection attempts reached');
        }
      };
    } catch (error) {
      logger.error('Failed to create WebSocket:', error);
      setIsConnected(false);
    }
  }, [getWebSocketUrl]);

  // Store connect function in ref to avoid circular dependency
  useEffect(() => {
    connectRef.current = connect;
  }, [connect]);

  useEffect(() => {
    if (typeof window === 'undefined') return;

    const token = localStorage.getItem('accessToken');
    if (!token) {
      logger.warn('No token available, skipping WebSocket connection');
      return;
    }

    // Use a setTimeout to defer connection setup to avoid cascading renders
    const timeoutId = setTimeout(() => {
      connect();
    }, 0);

    return () => {
      clearTimeout(timeoutId);
      if (reconnectTimeout.current) {
        clearTimeout(reconnectTimeout.current);
      }
      if (ws.current && ws.current.readyState === WebSocket.OPEN) {
        ws.current.close();
      }
    };
  }, [connect]);

  const getProgress = useCallback((asin: string): DownloadProgressEvent | undefined => {
    return progress[asin];
  }, [progress]);

  return {
    progress,
    isConnected,
    getProgress,
  };
}
