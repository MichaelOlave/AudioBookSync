import { useEffect, useState, useRef, useCallback } from 'react';

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
  const MAX_RECONNECT_ATTEMPTS = 5;
  const RECONNECT_DELAY = 3000;

  const getWebSocketUrl = useCallback(() => {
    if (typeof window === 'undefined') return '';

    const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
    const wsUrl = baseUrl.replace('http://', 'ws://').replace('https://', 'wss://');
    const token = localStorage.getItem('accessToken');

    if (!token) {
      console.warn('No access token available for WebSocket connection');
      return '';
    }

    const url = `${wsUrl}/ws/updates?token=${encodeURIComponent(token)}`;
    console.log('WebSocket URL:', url.replace(token, 'TOKEN_HIDDEN'));
    return url;
  }, []);

  const connect = useCallback(() => {
    const wsUrl = getWebSocketUrl();
    if (!wsUrl) {
      console.warn('Cannot connect to WebSocket: missing URL');
      return;
    }

    try {
      console.log('Connecting to WebSocket...');
      ws.current = new WebSocket(wsUrl);

      ws.current.onopen = () => {
        console.log('✓ WebSocket connected');
        setIsConnected(true);
        reconnectAttempts.current = 0;
      };

      ws.current.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          console.log('WebSocket message:', message.type);

          // Keep connection alive on any message
          setIsConnected(true);

          // Handle download.progress events
          if (message.type === 'download.progress' || message.type === 'download_progress') {
            const data = message.data;
            if (data.asin) {
              console.log(`✓ Update progress for ${data.asin}: ${data.progress_percent}%`);
              setProgress((prev) => ({
                ...prev,
                [data.asin]: data,
              }));
            }
          }
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error, 'Raw:', event.data);
        }
      };

      ws.current.onerror = (error) => {
        console.error('✗ WebSocket error:', error);
        setIsConnected(false);
      };

      ws.current.onclose = (event) => {
        console.log(`✗ WebSocket closed (code: ${event.code}, clean: ${event.wasClean})`);
        setIsConnected(false);

        // Attempt to reconnect
        if (reconnectAttempts.current < MAX_RECONNECT_ATTEMPTS) {
          reconnectAttempts.current += 1;
          console.log(`Attempting to reconnect (${reconnectAttempts.current}/${MAX_RECONNECT_ATTEMPTS})...`);

          reconnectTimeout.current = setTimeout(() => {
            connect();
          }, RECONNECT_DELAY);
        } else {
          console.error('Max reconnection attempts reached');
        }
      };
    } catch (error) {
      console.error('Failed to create WebSocket:', error);
      setIsConnected(false);
    }
  }, [getWebSocketUrl]);

  useEffect(() => {
    if (typeof window === 'undefined') return;

    const token = localStorage.getItem('accessToken');
    if (!token) {
      console.warn('No token available, skipping WebSocket connection');
      return;
    }

    connect();

    return () => {
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
