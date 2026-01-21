import { useState, useCallback } from 'react';
import { getAPIClient, APIError } from '@/lib/api/client';

export interface SyncStatus {
  sync_id: string;
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
  sync_type: string;
  books_found: number;
  books_added: number;
  books_downloaded: number;
  books_decrypted: number;
  errors_count: number;
  duration_seconds?: number;
  started_at: string;
  completed_at?: string;
}

export interface SyncHistoryResponse {
  items: SyncStatus[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

interface UseSyncState {
  currentSync: SyncStatus | null;
  syncHistory: SyncStatus[];
  loading: boolean;
  error: string | null;
}

export function useSync() {
  const [state, setState] = useState<UseSyncState>({
    currentSync: null,
    syncHistory: [],
    loading: false,
    error: null,
  });

  const apiClient = getAPIClient();

  const startSync = useCallback(
    async (syncType: string = 'full') => {
      setState((prev) => ({ ...prev, loading: true, error: null }));

      try {
        const response = (await apiClient.startSync(syncType)) as Record<string, unknown>;
        setState((prev) => ({
          ...prev,
          currentSync: {
            sync_id: response.sync_id as string,
            status: response.status as 'pending' | 'in_progress' | 'completed' | 'failed',
            sync_type: syncType,
            books_found: 0,
            books_added: 0,
            books_downloaded: 0,
            books_decrypted: 0,
            errors_count: 0,
            started_at: new Date().toISOString(),
          },
          loading: false,
        }));
        return response;
      } catch (err) {
        const error = err instanceof APIError ? err.message : 'Failed to start sync';
        setState((prev) => ({ ...prev, loading: false, error }));
        throw err;
      }
    },
    [apiClient]
  );

  const getSyncStatus = useCallback(
    async (syncId: string) => {
      try {
        const status = (await apiClient.getSyncStatus(syncId)) as SyncStatus;
        setState((prev) => ({
          ...prev,
          currentSync: status,
        }));
        return status;
      } catch (err) {
        const error = err instanceof APIError ? err.message : 'Failed to fetch sync status';
        setState((prev) => ({ ...prev, error }));
        throw err;
      }
    },
    [apiClient]
  );

  const getSyncHistory = useCallback(
    async (page: number = 1, pageSize: number = 10) => {
      setState((prev) => ({ ...prev, loading: true, error: null }));

      try {
        const response = (await apiClient.getSyncHistory(page, pageSize)) as SyncHistoryResponse;
        setState((prev) => ({
          ...prev,
          syncHistory: response.items,
          loading: false,
        }));
        return response;
      } catch (err) {
        const error = err instanceof APIError ? err.message : 'Failed to fetch sync history';
        setState((prev) => ({ ...prev, loading: false, error }));
        throw err;
      }
    },
    [apiClient]
  );

  return {
    currentSync: state.currentSync,
    syncHistory: state.syncHistory,
    loading: state.loading,
    error: state.error,
    startSync,
    getSyncStatus,
    getSyncHistory,
  };
}
