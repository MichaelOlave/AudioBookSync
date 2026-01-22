"use client";

import { useState, useEffect } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogClose,
} from "@/components/ui/dialog";
import {
  Pagination,
  PaginationContent,
  PaginationEllipsis,
  PaginationItem,
  PaginationLink,
  PaginationNext,
  PaginationPrevious,
} from "@/components/ui/pagination";
import {
  Search,
  Loader2,
  RefreshCw,
  CheckCircle2,
  AlertCircle,
  Cloud,
  Download,
} from "lucide-react";
import { useLibrary } from "@/hooks/use-library";
import { getAPIClient } from "@/lib/api/client";
import Link from "next/link";

const ITEMS_PER_PAGE = 12;

export default function AudibleLibraryPage() {
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedStatus, setSelectedStatus] = useState("all");
  const [audibleLinked, setAudibleLinked] = useState(true);
  const [checkingLink, setCheckingLink] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [downloadingAsins, setDownloadingAsins] = useState<Set<string>>(new Set());
  const [downloadMessage, setDownloadMessage] = useState<{
    type: "success" | "error";
    text: string;
  } | null>(null);
  const {
    books,
    loading,
    error,
    syncing,
    syncResult,
    fetchEntireLibrary,
    syncFromAudible,
  } = useLibrary();

  const apiClient = getAPIClient();

  // Check if Audible is linked on mount
  useEffect(() => {
    const checkAudibleLink = async () => {
      try {
        await apiClient.getAudibleCredentialsStatus();
        setAudibleLinked(true);
      } catch {
        setAudibleLinked(false);
      } finally {
        setCheckingLink(false);
      }
    };

    checkAudibleLink();
  }, [apiClient]);

  // Load entire library on mount
  useEffect(() => {
    fetchEntireLibrary();
  }, [fetchEntireLibrary]);

  const filteredBooks = books.filter((book) => {
    const matchesSearch =
      book.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      book.author.toLowerCase().includes(searchQuery.toLowerCase()) ||
      book.narrator.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStatus =
      selectedStatus === "all" ||
      (selectedStatus === "downloaded" && book.is_downloaded) ||
      (selectedStatus === "not_downloaded" && !book.is_downloaded);

    return matchesSearch && matchesStatus;
  });

  // Reset to page 1 when filters change
  useEffect(() => {
    setCurrentPage(1);
  }, [searchQuery, selectedStatus]);

  // Calculate pagination
  const totalPages = Math.ceil(filteredBooks.length / ITEMS_PER_PAGE);
  const startIndex = (currentPage - 1) * ITEMS_PER_PAGE;
  const endIndex = startIndex + ITEMS_PER_PAGE;
  const paginatedBooks = filteredBooks.slice(startIndex, endIndex);

  const handleSyncClick = async () => {
    setDialogOpen(true);
    await syncFromAudible();
  };

  const handleDownloadClick = async (asin: string, title: string) => {
    setDownloadingAsins((prev) => new Set(prev).add(asin));
    setDownloadMessage(null);

    try {
      await apiClient.startDownload(asin, title);
      setDownloadMessage({
        type: "success",
        text: `Download started for "${title}"`,
      });
    } catch (error) {
      setDownloadMessage({
        type: "error",
        text:
          error instanceof Error
            ? error.message
            : "Failed to start download",
      });
    } finally {
      setDownloadingAsins((prev) => {
        const next = new Set(prev);
        next.delete(asin);
        return next;
      });
    }
  };

  if (checkingLink) {
    return (
      <div className="space-y-8">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Audible Library</h1>
        </div>
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col w-full">
      {/* Header Section */}
      <div className="space-y-6 border-b pb-6 -mx-8 px-8">
        {/* Title and Button */}
        <div className="flex flex-col justify-between gap-4 md:flex-row md:items-start">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">
              Audible Library
            </h1>
            <p className="text-muted-foreground mt-2">
              Sync your Audible library and manage downloads
            </p>
          </div>
          {audibleLinked && (
            <Button
              onClick={handleSyncClick}
              disabled={syncing}
              className="gap-2"
            >
              {syncing ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Syncing...
                </>
              ) : (
                <>
                  <RefreshCw className="w-4 h-4" />
                  Sync from Audible
                </>
              )}
            </Button>
          )}
        </div>

        {/* Audible Not Linked Warning */}
        {!audibleLinked && (
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-yellow-600 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-yellow-800 font-medium">
                Audible account not linked
              </p>
              <p className="text-yellow-700 text-sm mt-1">
                Please link your Audible account in{" "}
                <Link
                  href="/dashboard/settings"
                  className="font-semibold underline"
                >
                  Settings
                </Link>{" "}
                to sync your library.
              </p>
            </div>
          </div>
        )}

        {/* Error Banner */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-red-800 font-medium">Sync failed</p>
              <p className="text-red-700 text-sm mt-1">{error}</p>
            </div>
          </div>
        )}

        {/* Filters */}
        <div className="space-y-4">
          <div className="flex flex-col gap-4 md:flex-row md:items-end md:gap-4">
            {/* Search */}
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <Input
                placeholder="Search by title, author, or narrator..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10"
              />
            </div>

            {/* Status Filter */}
            <Select value={selectedStatus} onValueChange={setSelectedStatus}>
              <SelectTrigger className="w-full md:w-40">
                <SelectValue placeholder="Status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All</SelectItem>
                <SelectItem value="downloaded">Downloaded</SelectItem>
                <SelectItem value="not_downloaded">Not Downloaded</SelectItem>
              </SelectContent>
            </Select>

            {/* Reset Filters */}
            {(searchQuery || selectedStatus !== "all") && (
              <Button
                variant="outline"
                onClick={() => {
                  setSearchQuery("");
                  setSelectedStatus("all");
                  setCurrentPage(1);
                }}
              >
                Reset
              </Button>
            )}
          </div>

          {/* Active Filters Display */}
          {(searchQuery || selectedStatus !== "all") && (
            <div className="flex flex-wrap gap-2">
              {searchQuery && (
                <Badge variant="secondary">Search: {searchQuery}</Badge>
              )}
              {selectedStatus !== "all" && (
                <Badge variant="secondary">
                  Status:{" "}
                  {selectedStatus === "downloaded"
                    ? "Downloaded"
                    : "Not Downloaded"}
                </Badge>
              )}
            </div>
          )}
        </div>

        {/* Results Count */}
        <div className="text-sm text-muted-foreground">
          {loading ? (
            <div className="flex items-center gap-2">
              <Loader2 className="w-4 h-4 animate-spin" />
              Loading audiobooks...
            </div>
          ) : (
            `Showing ${startIndex + 1}–${Math.min(endIndex, filteredBooks.length)} of ${filteredBooks.length} audiobooks${filteredBooks.length < books.length ? ` (filtered from ${books.length})` : ""}`
          )}
        </div>
      </div>

      {/* Content Area - Flex 1 to fill remaining space */}
      <div className="flex-1 overflow-auto flex flex-col">
        {/* Download Message Banner */}
        {downloadMessage && (
          <div
            className={`mx-8 mt-6 border rounded-lg p-4 flex items-start gap-3 ${
              downloadMessage.type === "success"
                ? "bg-green-50 border-green-200"
                : "bg-red-50 border-red-200"
            }`}
          >
            {downloadMessage.type === "success" ? (
              <CheckCircle2
                className={`w-5 h-5 flex-shrink-0 mt-0.5 ${
                  downloadMessage.type === "success"
                    ? "text-green-600"
                    : "text-red-600"
                }`}
              />
            ) : (
              <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
            )}
            <div>
              <p
                className={`font-medium ${
                  downloadMessage.type === "success"
                    ? "text-green-800"
                    : "text-red-800"
                }`}
              >
                {downloadMessage.text}
              </p>
            </div>
          </div>
        )}

        {/* Audiobooks Table */}
        {!loading && filteredBooks.length > 0 ? (
          <>
            <div className="flex-1 overflow-auto">
              <div className="border-b">
                <table className="w-full">
                  <thead className="sticky top-0 bg-muted/50">
                    <tr className="border-b">
                      <th className="px-6 py-3 text-left text-sm font-semibold">
                        Title
                      </th>
                      <th className="px-6 py-3 text-left text-sm font-semibold">
                        Author
                      </th>
                      <th className="px-6 py-3 text-left text-sm font-semibold">
                        Narrator
                      </th>
                      <th className="px-6 py-3 text-left text-sm font-semibold">
                        Duration
                      </th>
                      <th className="px-6 py-3 text-left text-sm font-semibold">
                        Series
                      </th>
                      <th className="px-8 py-3 text-center text-sm font-semibold">
                        Downloaded
                      </th>
                      <th className="px-6 py-3 text-center text-sm font-semibold">
                        Actions
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {paginatedBooks.map((book) => (
                      <tr
                        key={book.asin}
                        className="border-b hover:bg-muted/30 transition-colors"
                      >
                        <td className="px-6 py-4 text-sm font-medium">
                          {book.title}
                        </td>
                        <td className="px-6 py-4 text-sm text-muted-foreground">
                          {book.author}
                        </td>
                        <td className="px-6 py-4 text-sm text-muted-foreground">
                          {book.narrator}
                        </td>
                        <td className="px-6 py-4 text-sm text-muted-foreground">
                          {Math.round(book.runtime_min / 60)}h{" "}
                          {book.runtime_min % 60}m
                        </td>
                        <td className="px-6 py-4 text-sm text-muted-foreground">
                          {book.series_name || "General"}
                        </td>
                        <td className="px-6 py-4 text-center">
                          {book.is_downloaded ? (
                            <Badge className="bg-green-100 text-green-800 hover:bg-green-200">
                              Downloaded
                            </Badge>
                          ) : (
                            <Badge variant="outline">Not Downloaded</Badge>
                          )}
                        </td>
                        <td className="px-6 py-4 text-center">
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() =>
                              handleDownloadClick(book.asin, book.title)
                            }
                            disabled={downloadingAsins.has(book.asin)}
                            className="gap-2"
                          >
                            {downloadingAsins.has(book.asin) ? (
                              <>
                                <Loader2 className="w-4 h-4 animate-spin" />
                                Downloading...
                              </>
                            ) : (
                              <>
                                <Download className="w-4 h-4" />
                                Download
                              </>
                            )}
                          </Button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Pagination Footer */}
            {totalPages > 1 && (
              <div className="py-4 border-t flex justify-center bg-muted/30 -mx-8 px-8">
                <Pagination>
                  <PaginationContent>
                    <PaginationItem>
                      <PaginationPrevious
                        onClick={() =>
                          setCurrentPage(Math.max(1, currentPage - 1))
                        }
                        className={
                          currentPage === 1
                            ? "pointer-events-none opacity-50"
                            : "cursor-pointer"
                        }
                      />
                    </PaginationItem>

                    {/* Page Numbers */}
                    {Array.from({ length: totalPages }, (_, i) => i + 1).map(
                      (pageNum) => {
                        // Show first 2, last 2, and current page with neighbors
                        const shouldShow =
                          pageNum <= 2 ||
                          pageNum > totalPages - 2 ||
                          Math.abs(pageNum - currentPage) <= 1;

                        if (!shouldShow) {
                          // Show ellipsis between gaps
                          const prevPageShown =
                            pageNum - 1 <= 2 ||
                            pageNum - 1 > totalPages - 2 ||
                            Math.abs(pageNum - 1 - currentPage) <= 1;
                          if (prevPageShown) {
                            return (
                              <PaginationItem key={`ellipsis-${pageNum}`}>
                                <PaginationEllipsis />
                              </PaginationItem>
                            );
                          }
                          return null;
                        }

                        return (
                          <PaginationItem key={pageNum}>
                            <PaginationLink
                              onClick={() => setCurrentPage(pageNum)}
                              isActive={pageNum === currentPage}
                              className="cursor-pointer"
                            >
                              {pageNum}
                            </PaginationLink>
                          </PaginationItem>
                        );
                      },
                    )}

                    <PaginationItem>
                      <PaginationNext
                        onClick={() =>
                          setCurrentPage(Math.min(totalPages, currentPage + 1))
                        }
                        className={
                          currentPage === totalPages
                            ? "pointer-events-none opacity-50"
                            : "cursor-pointer"
                        }
                      />
                    </PaginationItem>
                  </PaginationContent>
                </Pagination>
              </div>
            )}
          </>
        ) : !loading ? (
          <div className="flex-1 flex flex-col items-center justify-center">
            <Cloud className="w-12 h-12 text-muted-foreground mb-4 opacity-50" />
            <p className="text-muted-foreground mb-4">
              {audibleLinked
                ? "No audiobooks synced yet. Click 'Sync from Audible' to import your Audible library."
                : "Link your Audible account to see your library."}
            </p>
            {audibleLinked && (
              <Button
                onClick={handleSyncClick}
                disabled={syncing}
                className="gap-2"
              >
                {syncing ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Syncing...
                  </>
                ) : (
                  <>
                    <RefreshCw className="w-4 h-4" />
                    Sync from Audible
                  </>
                )}
              </Button>
            )}
          </div>
        ) : (
          <div className="flex-1 flex items-center justify-center">
            <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
          </div>
        )}
      </div>

      {/* Sync Result Modal */}
      <Dialog
        open={dialogOpen && (syncing || !!syncResult)}
        onOpenChange={setDialogOpen}
      >
        <DialogContent className="sm:max-w-[425px]">
          <DialogHeader>
            <DialogTitle>Sync Complete</DialogTitle>
            <DialogClose />
          </DialogHeader>
          <div className="space-y-4 py-4">
            {syncing ? (
              <div className="flex items-center gap-2">
                <Loader2 className="w-4 h-4 animate-spin text-blue-600" />
                <span className="text-sm">Syncing your Audible library...</span>
              </div>
            ) : syncResult ? (
              <>
                <div className="flex items-center gap-2 text-green-600">
                  <CheckCircle2 className="w-5 h-5" />
                  <span className="font-medium">Sync completed!</span>
                </div>
                <div className="space-y-2">
                  <div className="text-sm">
                    <span className="font-medium">Books saved:</span>{" "}
                    <span>{syncResult.books_saved || 0}</span>
                  </div>
                  <div className="text-sm">
                    <span className="font-medium">Books failed:</span>{" "}
                    <span>{syncResult.books_failed || 0}</span>
                  </div>
                  <div className="text-sm">
                    <span className="font-medium">Total fetched:</span>{" "}
                    <span>{syncResult.total_fetched || 0}</span>
                  </div>
                </div>
              </>
            ) : null}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
