import { useState, useCallback, useEffect } from 'react';
import { getAPIClient, APIError } from '@/lib/api/client';

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
}

export interface LibraryResponse {
  items: Book[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

interface UseLibraryState {
  books: Book[];
  loading: boolean;
  error: string | null;
  total: number;
  page: number;
  pages: number;
}

export function useLibrary() {
  const [state, setState] = useState<UseLibraryState>({
    books: [],
    loading: false,
    error: null,
    total: 0,
    page: 1,
    pages: 1,
  });

  const apiClient = getAPIClient();

  const fetchLibrary = useCallback(
    async (pageNum: number = 1, pageSize: number = 50) => {
      setState((prev) => ({ ...prev, loading: true, error: null }));

      try {
        const response = (await apiClient.getLibrary(pageNum, pageSize)) as LibraryResponse;
        setState({
          books: response.items,
          loading: false,
          error: null,
          total: response.total,
          page: response.page,
          pages: response.pages,
        });
      } catch (err) {
        const error = err instanceof APIError ? err.message : 'Failed to fetch library';
        setState((prev) => ({
          ...prev,
          loading: false,
          error,
        }));
      }
    },
    [apiClient]
  );

  const getBook = useCallback(
    async (asin: string) => {
      try {
        return await apiClient.getBook(asin);
      } catch (err) {
        const error = err instanceof APIError ? err.message : 'Failed to fetch book';
        setState((prev) => ({ ...prev, error }));
        throw err;
      }
    },
    [apiClient]
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
        const error = err instanceof APIError ? err.message : 'Failed to delete book';
        setState((prev) => ({ ...prev, error }));
        throw err;
      }
    },
    [apiClient]
  );

  return {
    books: state.books,
    loading: state.loading,
    error: state.error,
    total: state.total,
    page: state.page,
    pages: state.pages,
    fetchLibrary,
    getBook,
    deleteBook,
  };
}
