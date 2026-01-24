import { useState, useCallback } from 'react';
import { getAPIClient, APIError } from '@/lib/api/client';

export interface Schedule {
  schedule_id: string;
  user_id: string;
  interval_minutes: number;
  action: 'metadata_only' | 'download';
  enabled: boolean;
  last_run_at: string | null;
  next_run_at: string;
  created_at: string;
  updated_at: string;
}

export interface SchedulesResponse {
  items: Schedule[];
  total: number;
}

export interface CreateScheduleData {
  interval_minutes: number;
  action: 'metadata_only' | 'download';
  enabled: boolean;
  start_at?: string;
}

export interface UpdateScheduleData {
  interval_minutes?: number;
  action?: 'metadata_only' | 'download';
  enabled?: boolean;
}

interface UseSchedulesState {
  schedules: Schedule[];
  loading: boolean;
  error: string | null;
  total: number;
}

export function useSchedules() {
  const [state, setState] = useState<UseSchedulesState>({
    schedules: [],
    loading: false,
    error: null,
    total: 0,
  });

  const apiClient = getAPIClient();

  const getSchedules = useCallback(async () => {
    setState((prev) => ({ ...prev, loading: true, error: null }));

    try {
      const response = (await apiClient.get('/tasks/schedules')) as SchedulesResponse;
      setState({
        schedules: response.items,
        loading: false,
        error: null,
        total: response.total,
      });
      return response;
    } catch (err) {
      const error = err instanceof APIError ? err.message : 'Failed to fetch schedules';
      setState((prev) => ({
        ...prev,
        loading: false,
        error,
      }));
      throw err;
    }
  }, [apiClient]);

  const createSchedule = useCallback(
    async (data: CreateScheduleData) => {
      try {
        const response = (await apiClient.post('/tasks/schedules', data)) as Schedule;
        // Refresh schedules list after creation
        await getSchedules();
        return response;
      } catch (err) {
        const error = err instanceof APIError ? err.message : 'Failed to create schedule';
        setState((prev) => ({ ...prev, error }));
        throw err;
      }
    },
    [apiClient, getSchedules]
  );

  const updateSchedule = useCallback(
    async (scheduleId: string, data: UpdateScheduleData) => {
      try {
        const response = (await apiClient.patch(
          `/tasks/schedules/${scheduleId}`,
          data
        )) as Schedule;
        // Refresh schedules list after update
        await getSchedules();
        return response;
      } catch (err) {
        const error = err instanceof APIError ? err.message : 'Failed to update schedule';
        setState((prev) => ({ ...prev, error }));
        throw err;
      }
    },
    [apiClient, getSchedules]
  );

  const deleteSchedule = useCallback(
    async (scheduleId: string) => {
      try {
        await apiClient.delete(`/tasks/schedules/${scheduleId}`);
        // Refresh schedules list after deletion
        await getSchedules();
      } catch (err) {
        const error = err instanceof APIError ? err.message : 'Failed to delete schedule';
        setState((prev) => ({ ...prev, error }));
        throw err;
      }
    },
    [apiClient, getSchedules]
  );

  return {
    schedules: state.schedules,
    loading: state.loading,
    error: state.error,
    total: state.total,
    getSchedules,
    createSchedule,
    updateSchedule,
    deleteSchedule,
  };
}
