import { useState, useCallback } from "react";
import { getAPIClient, APIError } from "@/lib/api/client";

export interface Book {
  asin: string;
  title: string;
  author: string;
  narrator: string;
  series_name?: string;
  description?: string;
  rating?: number;
  runtime_min: number;
  purchase_date?: string;
  is_downloaded: boolean;
  is_decrypted: boolean;
  cover_art_url?: string;
}

export interface LibraryResponse {
  items: Book[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface SyncResponse {
  books_failed: number;
  books_saved: number;
  total_fetched: number;
  user_id: string;
}

interface UseLibraryState {
  books: Book[];
  loading: boolean;
  error: string | null;
  total: number;
  page: number;
  pages: number;
  syncing: boolean;
  syncResult: SyncResponse | null;
}

export function useLibrary() {
  const [state, setState] = useState<UseLibraryState>({
    books: [],
    loading: false,
    error: null,
    total: 0,
    page: 1,
    pages: 1,
    syncing: false,
    syncResult: null,
  });

  const apiClient = getAPIClient();

  const fetchLibrary = useCallback(
    async (pageNum: number = 1, pageSize: number = 50) => {
      setState((prev) => ({ ...prev, loading: true, error: null }));

      try {
        const response = (await apiClient.getLibrary(
          pageNum,
          pageSize,
        )) as LibraryResponse;
        setState((prev) => ({
          ...prev,
          books: response.items,
          loading: false,
          error: null,
          total: response.total,
          page: response.page,
          pages: response.pages,
        }));
      } catch (err) {
        const error =
          err instanceof APIError ? err.message : "Failed to fetch library";
        setState((prev) => ({
          ...prev,
          loading: false,
          error,
        }));
      }
    },
    [apiClient],
  );

  const fetchEntireLibrary = useCallback(
    async (pageSize: number = 100) => {
      setState((prev) => ({ ...prev, loading: true, error: null }));

      try {
        let currentPage = 1;
        let allBooks: Book[] = [];
        let totalPages = 0;

        while (true) {
          const response = (await apiClient.getLibrary(
            currentPage,
            pageSize,
          )) as LibraryResponse;

          allBooks = [...allBooks, ...response.items];
          totalPages = response.pages;

          if (currentPage >= totalPages) {
            break;
          }

          currentPage++;
        }

        setState((prev) => ({
          ...prev,
          books: allBooks,
          loading: false,
          error: null,
          total: allBooks.length,
          page: 1,
          pages: 1,
        }));
      } catch (err) {
        const error =
          err instanceof APIError ? err.message : "Failed to fetch library";
        setState((prev) => ({
          ...prev,
          loading: false,
          error,
        }));
      }
    },
    [apiClient],
  );

  const fetchDashboard = useCallback(
    async (downloadOnly?: boolean) => {
      setState((prev) => ({ ...prev, loading: true, error: null }));

      try {
        const response = (await apiClient.getDashboard(downloadOnly)) as Array<{
          book: Book;
          metadata?: unknown;
        }>;
        const allBooks = response.map((item) => item.book) || [];

        setState((prev) => ({
          ...prev,
          books: allBooks,
          loading: false,
          error: null,
          total: allBooks.length,
          page: 1,
          pages: 1,
        }));
      } catch (err) {
        const error =
          err instanceof APIError ? err.message : "Failed to fetch dashboard";
        setState((prev) => ({
          ...prev,
          loading: false,
          error,
        }));
      }
    },
    [apiClient],
  );

  const getBook = useCallback(
    async (asin: string) => {
      try {
        return await apiClient.getBook(asin);
      } catch (err) {
        const error =
          err instanceof APIError ? err.message : "Failed to fetch book";
        setState((prev) => ({ ...prev, error }));
        throw err;
      }
    },
    [apiClient],
  );

  const deleteBook = useCallback(
    async (asin: string) => {
      try {
        await apiClient.deleteBook(asin);
        setState((prev) => ({
          ...prev,
          books: prev.books.filter((b) => b.asin !== asin),
        }));
      } catch (err) {
        const error =
          err instanceof APIError ? err.message : "Failed to delete book";
        setState((prev) => ({ ...prev, error }));
        throw err;
      }
    },
    [apiClient],
  );

  const syncFromAudible = useCallback(async () => {
    console.log("Starting syncFromAudible...");
    setState((prev) => ({
      ...prev,
      syncing: true,
      error: null,
      syncResult: null,
    }));

    try {
      let currentPage = 1;
      let totalSaved = 0;
      let totalFailed = 0;
      const pageSize = 500;

      console.log("Beginning pagination loop...");
      // Keep fetching pages until all books are retrieved
      while (true) {
        console.log(`Fetching page ${currentPage}...`);
        const response = (await apiClient.fetchFromAudible(
          pageSize,
          currentPage,
        )) as SyncResponse;

        console.log("Full response:", response);
        const fetched = response.total_fetched || 0;
        const saved = response.books_saved || 0;
        const failed = response.books_failed || 0;

        totalSaved += saved;
        totalFailed += failed;

        console.log(
          `Fetched page ${currentPage}: ${fetched} books (saved: ${saved}, failed: ${failed}), cumulative: ${totalSaved} saved, ${totalFailed} failed`,
        );

        // Stop if no more books were fetched on this page
        if (fetched === 0) {
          console.log("Pagination complete");
          break;
        }

        currentPage++;
      }

      console.log(
        `Sync complete. Total saved: ${totalSaved}, Total failed: ${totalFailed}`,
      );
      const syncResult: SyncResponse = {
        books_saved: totalSaved,
        books_failed: totalFailed,
        total_fetched: totalSaved + totalFailed,
        user_id: "",
      };

      setState((prev) => ({
        ...prev,
        syncResult,
      }));

      // Refresh library after successful sync
      await fetchLibrary(1, 50);
    } catch (err) {
      console.error("Error in syncFromAudible:", err);
      const error =
        err instanceof APIError ? err.message : "Failed to fetch from Audible";
      setState((prev) => ({
        ...prev,
        error,
      }));
    } finally {
      setState((prev) => ({
        ...prev,
        syncing: false,
      }));
    }
  }, [apiClient, fetchLibrary]);

  return {
    books: state.books,
    loading: state.loading,
    error: state.error,
    total: state.total,
    page: state.page,
    pages: state.pages,
    syncing: state.syncing,
    syncResult: state.syncResult,
    fetchLibrary,
    fetchEntireLibrary,
    fetchDashboard,
    getBook,
    deleteBook,
    syncFromAudible,
  };
}
