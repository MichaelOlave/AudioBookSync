import { useState, useCallback } from 'react';
import { getAPIClient, APIError } from '@/lib/api/client';

export interface Download {
  download_id: string;
  asin: string;
  title: string;
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
  progress_percent: number;
  downloaded_bytes: number;
  total_bytes: number;
  error_message?: string;
  completed_at?: string;
}

export interface DownloadsResponse {
  items: Download[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

interface UseDownloadsState {
  downloads: Download[];
  loading: boolean;
  error: string | null;
  total: number;
}

export function useDownloads() {
  const [state, setState] = useState<UseDownloadsState>({
    downloads: [],
    loading: false,
    error: null,
    total: 0,
  });

  const apiClient = getAPIClient();

  const startDownload = useCallback(
    async (asin: string, title: string) => {
      try {
        const response = await apiClient.startDownload(asin, title);
        return response;
      } catch (err) {
        const error = err instanceof APIError ? err.message : 'Failed to start download';
        setState((prev) => ({ ...prev, error }));
        throw err;
      }
    },
    [apiClient]
  );

  const getDownloads = useCallback(
    async (status?: string, page: number = 1, pageSize: number = 50) => {
      setState((prev) => ({ ...prev, loading: true, error: null }));

      try {
        const response = (await apiClient.getDownloads(status, page, pageSize)) as DownloadsResponse;
        setState({
          downloads: response.items,
          loading: false,
          error: null,
          total: response.total,
        });
        return response;
      } catch (err) {
        const error = err instanceof APIError ? err.message : 'Failed to fetch downloads';
        setState((prev) => ({
          ...prev,
          loading: false,
          error,
        }));
        throw err;
      }
    },
    [apiClient]
  );

  const getDownloadStatus = useCallback(
    async (downloadId: string) => {
      try {
        return await apiClient.getDownloadStatus(downloadId);
      } catch (err) {
        const error = err instanceof APIError ? err.message : 'Failed to fetch download status';
        setState((prev) => ({ ...prev, error }));
        throw err;
      }
    },
    [apiClient]
  );

  return {
    downloads: state.downloads,
    loading: state.loading,
    error: state.error,
    total: state.total,
    startDownload,
    getDownloads,
    getDownloadStatus,
  };
}
