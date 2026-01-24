import { useState, useCallback } from "react";
import { getAPIClient, APIError } from "@/lib/api/client";
import type {
  Family,
  FamilyDetail,
  FamilyMember,
  FamilyCreateRequest,
  FamilyUpdateRequest,
  FamilyMemberAddRequest,
  FamilyTransferOwnerRequest,
} from "@/lib/api/types";

interface UseFamiliesState {
  family: Family | null;
  members: FamilyMember[];
  loading: boolean;
  error: string | null;
  actionLoading: boolean;
  actionError: string | null;
}

export function useFamilies() {
  const [state, setState] = useState<UseFamiliesState>({
    family: null,
    members: [],
    loading: false,
    error: null,
    actionLoading: false,
    actionError: null,
  });

  const apiClient = getAPIClient();

  const fetchMyFamily = useCallback(async () => {
    setState((prev) => ({ ...prev, loading: true, error: null }));

    try {
      const response = (await apiClient.request<FamilyDetail>(
        "GET",
        "/families/me"
      )) as FamilyDetail;
      setState((prev) => ({
        ...prev,
        family: response.family,
        members: response.members,
        loading: false,
        error: null,
      }));
    } catch (err) {
      const error =
        err instanceof APIError ? err.message : "Failed to fetch family";
      setState((prev) => ({
        ...prev,
        loading: false,
        error,
      }));
    }
  }, [apiClient]);

  const fetchFamily = useCallback(
    async (familyId: string) => {
      setState((prev) => ({ ...prev, loading: true, error: null }));

      try {
        const response = (await apiClient.request<FamilyDetail>(
          "GET",
          `/families/${familyId}`
        )) as FamilyDetail;
        setState((prev) => ({
          ...prev,
          family: response.family,
          members: response.members,
          loading: false,
          error: null,
        }));
      } catch (err) {
        const error =
          err instanceof APIError ? err.message : "Failed to fetch family";
        setState((prev) => ({
          ...prev,
          loading: false,
          error,
        }));
      }
    },
    [apiClient]
  );

  const createFamily = useCallback(
    async (data: FamilyCreateRequest) => {
      setState((prev) => ({ ...prev, actionLoading: true, actionError: null }));

      try {
        const response = (await apiClient.request<FamilyDetail>(
          "POST",
          "/families",
          {
            body: data,
          }
        )) as FamilyDetail;
        setState((prev) => ({
          ...prev,
          family: response.family,
          members: response.members,
          actionLoading: false,
          actionError: null,
        }));
      } catch (err) {
        const error =
          err instanceof APIError
            ? err.message
            : "Failed to create family";
        setState((prev) => ({
          ...prev,
          actionLoading: false,
          actionError: error,
        }));
        throw err;
      }
    },
    [apiClient]
  );

  const updateFamily = useCallback(
    async (familyId: string, data: FamilyUpdateRequest) => {
      setState((prev) => ({ ...prev, actionLoading: true, actionError: null }));

      try {
        const response = (await apiClient.request<FamilyDetail>(
          "PATCH",
          `/families/${familyId}`,
          {
            body: data,
          }
        )) as FamilyDetail;
        setState((prev) => ({
          ...prev,
          family: response.family,
          members: response.members,
          actionLoading: false,
          actionError: null,
        }));
      } catch (err) {
        const error =
          err instanceof APIError
            ? err.message
            : "Failed to update family";
        setState((prev) => ({
          ...prev,
          actionLoading: false,
          actionError: error,
        }));
        throw err;
      }
    },
    [apiClient]
  );

  const addMember = useCallback(
    async (familyId: string, data: FamilyMemberAddRequest) => {
      setState((prev) => ({ ...prev, actionLoading: true, actionError: null }));

      try {
        const response = (await apiClient.request<FamilyDetail>(
          "POST",
          `/families/${familyId}/members`,
          {
            body: data,
          }
        )) as FamilyDetail;
        setState((prev) => ({
          ...prev,
          family: response.family,
          members: response.members,
          actionLoading: false,
          actionError: null,
        }));
      } catch (err) {
        const error =
          err instanceof APIError ? err.message : "Failed to add member";
        setState((prev) => ({
          ...prev,
          actionLoading: false,
          actionError: error,
        }));
        throw err;
      }
    },
    [apiClient]
  );

  const removeMember = useCallback(
    async (familyId: string, memberId: string) => {
      setState((prev) => ({ ...prev, actionLoading: true, actionError: null }));

      try {
        const response = (await apiClient.request<FamilyDetail>(
          "DELETE",
          `/families/${familyId}/members/${memberId}`
        )) as FamilyDetail;
        setState((prev) => ({
          ...prev,
          family: response.family,
          members: response.members,
          actionLoading: false,
          actionError: null,
        }));
      } catch (err) {
        const error =
          err instanceof APIError
            ? err.message
            : "Failed to remove member";
        setState((prev) => ({
          ...prev,
          actionLoading: false,
          actionError: error,
        }));
        throw err;
      }
    },
    [apiClient]
  );

  const deleteFamily = useCallback(
    async (familyId: string) => {
      setState((prev) => ({ ...prev, actionLoading: true, actionError: null }));

      try {
        await apiClient.request("DELETE", `/families/${familyId}`);
        setState((prev) => ({
          ...prev,
          family: null,
          members: [],
          actionLoading: false,
          actionError: null,
        }));
      } catch (err) {
        const error =
          err instanceof APIError ? err.message : "Failed to delete family";
        setState((prev) => ({
          ...prev,
          actionLoading: false,
          actionError: error,
        }));
        throw err;
      }
    },
    [apiClient]
  );

  const transferOwnership = useCallback(
    async (familyId: string, data: FamilyTransferOwnerRequest) => {
      setState((prev) => ({ ...prev, actionLoading: true, actionError: null }));

      try {
        const response = (await apiClient.request<FamilyDetail>(
          "PATCH",
          `/families/${familyId}/owner`,
          {
            body: data,
          }
        )) as FamilyDetail;
        setState((prev) => ({
          ...prev,
          family: response.family,
          members: response.members,
          actionLoading: false,
          actionError: null,
        }));
      } catch (err) {
        const error =
          err instanceof APIError
            ? err.message
            : "Failed to transfer ownership";
        setState((prev) => ({
          ...prev,
          actionLoading: false,
          actionError: error,
        }));
        throw err;
      }
    },
    [apiClient]
  );

  const updateLibrarySharing = useCallback(
    async (shareLibrary: boolean) => {
      setState((prev) => ({ ...prev, actionLoading: true, actionError: null }));

      try {
        await apiClient.request("PATCH", "/users/me/family", {
          body: {
            share_library_with_family: shareLibrary,
          },
        });
        // Refresh family data to get updated member list
        await fetchMyFamily();
        setState((prev) => ({
          ...prev,
          actionLoading: false,
          actionError: null,
        }));
      } catch (err) {
        const error =
          err instanceof APIError
            ? err.message
            : "Failed to update library sharing";
        setState((prev) => ({
          ...prev,
          actionLoading: false,
          actionError: error,
        }));
        throw err;
      }
    },
    [apiClient, fetchMyFamily]
  );

  return {
    family: state.family,
    members: state.members,
    loading: state.loading,
    error: state.error,
    actionLoading: state.actionLoading,
    actionError: state.actionError,
    fetchMyFamily,
    fetchFamily,
    createFamily,
    updateFamily,
    addMember,
    removeMember,
    deleteFamily,
    transferOwnership,
    updateLibrarySharing,
  };
}
