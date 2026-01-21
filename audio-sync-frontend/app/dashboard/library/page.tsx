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
import { AudiobookCard } from "@/components/audiobook-card";
import { Search, Loader2 } from "lucide-react";
import { useLibrary } from "@/hooks/use-library";

export default function LibraryPage() {
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedStatus, setSelectedStatus] = useState("all");
  const { books, loading, error, fetchLibrary } = useLibrary();

  useEffect(() => {
    fetchLibrary(1, 50);
  }, []);

  const filteredBooks = books.filter((book) => {
    const matchesSearch =
      book.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      book.author.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStatus =
      selectedStatus === "all" ||
      (selectedStatus === "downloaded" && book.is_downloaded) ||
      (selectedStatus === "pending" && !book.is_downloaded);

    return matchesSearch && matchesStatus;
  });

  if (error) {
    return (
      <div className="space-y-8">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">My Library</h1>
        </div>
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
          {error}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">My Library</h1>
        <p className="text-muted-foreground mt-2">
          Browse and manage your audiobook collection
        </p>
      </div>

      {/* Filters */}
      <div className="space-y-4">
        <div className="flex flex-col gap-4 md:flex-row md:items-end md:gap-4">
          {/* Search */}
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <Input
              placeholder="Search by title or author..."
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
              <SelectItem value="pending">Not Downloaded</SelectItem>
            </SelectContent>
          </Select>

          {/* Reset Filters */}
          {(searchQuery || selectedStatus !== "all") && (
            <Button
              variant="outline"
              onClick={() => {
                setSearchQuery("");
                setSelectedStatus("all");
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
              <Badge variant="secondary">
                Search: {searchQuery}
              </Badge>
            )}
            {selectedStatus !== "all" && (
              <Badge variant="secondary">
                Status: {selectedStatus === "downloaded" ? "Downloaded" : "Not Downloaded"}
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
          `Showing ${filteredBooks.length} of ${books.length} audiobooks`
        )}
      </div>

      {/* Audiobooks Grid */}
      {!loading && filteredBooks.length > 0 ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          {filteredBooks.map((book) => (
            <AudiobookCard
              key={book.asin}
              id={book.asin}
              title={book.title}
              author={book.author}
              narrator={book.narrator}
              cover=""
              duration={`${Math.round(book.runtime_min / 60)}h ${book.runtime_min % 60}m`}
              category={book.series_name || "General"}
              downloaded={book.is_downloaded}
            />
          ))}
        </div>
      ) : !loading ? (
        <div className="text-center py-12">
          <p className="text-muted-foreground">No audiobooks found matching your filters</p>
          <Button
            variant="outline"
            className="mt-4"
            onClick={() => {
              setSearchQuery("");
              setSelectedStatus("all");
            }}
          >
            Clear Filters
          </Button>
        </div>
      ) : null}
    </div>
  );
}
