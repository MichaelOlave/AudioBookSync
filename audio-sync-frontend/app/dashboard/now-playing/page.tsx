"use client";

import { useState, useEffect, useRef } from "react";
import Image from "next/image";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Play,
  Pause,
  SkipBack,
  SkipForward,
  Volume2,
  List,
  Loader2,
} from "lucide-react";
import { useLibrary } from "@/hooks/use-library";
import { getAPIClient } from "@/lib/api/client";

export default function NowPlayingPage() {
  const { books, loading, fetchDashboard } = useLibrary();
  const [isPlaying, setIsPlaying] = useState(false);
  const [isLoadingAudio, setIsLoadingAudio] = useState(false);
  const [chapters, setChapters] = useState<
    Array<{ start_offset_ms: number; title: string }>
  >([]);
  const [isLoadingChapters, setIsLoadingChapters] = useState(false);
  const audioRef = useRef<HTMLAudioElement>(null);
  const blobUrlRef = useRef<string | null>(null);
  const progressIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const apiClient = getAPIClient();

  useEffect(() => {
    fetchDashboard(true);
  }, [fetchDashboard]);

  // Load progress and chapters when book is available
  useEffect(() => {
    if (books.length > 0) {
      loadProgress();
      loadChapters();
    }
  }, [books.length]);

  const loadChapters = async () => {
    if (books.length === 0) return;
    try {
      setIsLoadingChapters(true);
      const chaptersData = (await apiClient.getChapters(
        books[0].asin
      )) as Array<{
        start_offset_ms: number;
        title: string;
      }> | null;
      if (chaptersData) {
        setChapters(chaptersData);
      }
    } catch (error) {
      console.error("Failed to load chapters:", error);
    } finally {
      setIsLoadingChapters(false);
    }
  };

  const loadProgress = async () => {
    if (books.length === 0 || !audioRef.current) return;
    try {
      const progress = (await apiClient.getProgress(books[0].asin)) as {
        position_ms: number;
      } | null;
      if (progress) {
        audioRef.current.currentTime = progress.position_ms / 1000;
      }
    } catch (error) {
      console.error("Failed to load progress:", error);
    }
  };

  const saveProgress = async () => {
    if (!audioRef.current || books.length === 0) return;

    const currentBook = books[0];
    const duration_ms = (audioRef.current.duration || 0) * 1000;
    const position_ms = audioRef.current.currentTime * 1000;
    const percent_complete =
      duration_ms > 0
        ? Math.round((position_ms / duration_ms) * 100)
        : 0;

    try {
      await apiClient.updateProgress(currentBook.asin, {
        position_ms: Math.round(position_ms),
        percent_complete,
        is_finished: percent_complete >= 95,
      });
    } catch (error) {
      console.error("Failed to save progress:", error);
    }
  };

  // Setup progress tracking interval
  useEffect(() => {
    if (isPlaying) {
      progressIntervalRef.current = setInterval(() => {
        saveProgress();
      }, 7000); // Update every 7 seconds

      return () => {
        if (progressIntervalRef.current) {
          clearInterval(progressIntervalRef.current);
        }
      };
    } else {
      if (progressIntervalRef.current) {
        clearInterval(progressIntervalRef.current);
      }
    }
  }, [isPlaying]);

  // Cleanup and save progress on unmount
  useEffect(() => {
    return () => {
      if (blobUrlRef.current) {
        URL.revokeObjectURL(blobUrlRef.current);
      }
      if (progressIntervalRef.current) {
        clearInterval(progressIntervalRef.current);
      }
      // Save progress on unmount
      saveProgress();
    };
  }, []);

  const currentBook = books.length > 0 ? books[0] : null;

  if (!currentBook) {
    return (
      <div className="space-y-8 max-w-4xl mx-auto">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Now Playing</h1>
          <p className="text-muted-foreground mt-2">
            Continue your listening journey
          </p>
        </div>
        <Card className="p-8 border border-border">
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
          </div>
        </Card>
      </div>
    );
  }

  const duration = `${Math.round(currentBook.runtime_min / 60)}h ${currentBook.runtime_min % 60}m`;

  const handlePlay = async () => {
    if (!audioRef.current) return;

    if (isPlaying) {
      audioRef.current.pause();
      setIsPlaying(false);
      await saveProgress();
    } else {
      try {
        setIsLoadingAudio(true);
        const blob = await apiClient.getAudiobook(currentBook.asin);

        if (blobUrlRef.current) {
          URL.revokeObjectURL(blobUrlRef.current);
        }

        const blobUrl = URL.createObjectURL(blob);
        blobUrlRef.current = blobUrl;
        audioRef.current.src = blobUrl;
        await audioRef.current.play();
        setIsPlaying(true);
      } catch (error) {
        console.error("Play failed:", error);
      } finally {
        setIsLoadingAudio(false);
      }
    }
  };

  return (
    <div className="space-y-8 max-w-4xl mx-auto">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Now Playing</h1>
        <p className="text-muted-foreground mt-2">
          Continue your listening journey
        </p>
      </div>

      {/* Now Playing Card */}
      <Card className="p-8 border border-border">
        <div className="space-y-6">
          {/* Book Cover */}
          {currentBook.cover_art_url ? (
            <div className="relative w-full h-60 rounded-lg overflow-hidden">
              <Image
                src={currentBook.cover_art_url}
                alt={`${currentBook.title} cover`}
                fill
                className="object-cover w-full h-full"
              />
            </div>
          ) : (
            <div className="w-full h-60 bg-gradient-to-br from-purple-400 to-blue-500 rounded-lg flex items-center justify-center text-white">
              <div className="text-center">
                <div className="text-6xl mb-2">♪</div>
                <p className="text-lg font-semibold">{currentBook.title}</p>
              </div>
            </div>
          )}

          {/* Book Info */}
          <div className="space-y-2">
            <h2 className="text-2xl font-bold">{currentBook.title}</h2>
            <p className="text-muted-foreground">by {currentBook.author}</p>
            <div className="flex gap-2 pt-2">
              <Badge variant="outline">{currentBook.series_name || "General"}</Badge>
              <Badge variant="outline">Narrator: {currentBook.narrator}</Badge>
            </div>
            {currentBook.description && (
              <p className="text-sm text-muted-foreground leading-relaxed pt-4">
                {currentBook.description}
              </p>
            )}
          </div>

          {/* Audio Player */}
          <audio
            ref={audioRef}
            className="w-full"
            controls
            onPlay={() => setIsPlaying(true)}
            onPause={() => setIsPlaying(false)}
            onEnded={() => setIsPlaying(false)}
          />

          {/* Chapters */}
          {isLoadingChapters ? (
            <div className="flex items-center justify-center py-4">
              <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
            </div>
          ) : chapters.length > 0 ? (
            <div className="space-y-2">
              <h3 className="font-semibold text-sm">Chapters</h3>
              <div className="max-h-64 overflow-y-auto space-y-2">
                {chapters.map((chapter, index) => {
                  const hours = Math.floor(chapter.start_offset_ms / 3600000);
                  const minutes = Math.floor(
                    (chapter.start_offset_ms % 3600000) / 60000
                  );
                  const timeStr = `${hours}:${minutes.toString().padStart(2, "0")}`;

                  const handleChapterClick = async () => {
                    if (!audioRef.current || !currentBook) return;

                    // If audio isn't loaded yet, load it first
                    if (!audioRef.current.src) {
                      try {
                        setIsLoadingAudio(true);
                        const blob = await apiClient.getAudiobook(
                          currentBook.asin
                        );

                        if (blobUrlRef.current) {
                          URL.revokeObjectURL(blobUrlRef.current);
                        }

                        const blobUrl = URL.createObjectURL(blob);
                        blobUrlRef.current = blobUrl;
                        audioRef.current.src = blobUrl;
                      } catch (error) {
                        console.error("Failed to load audio:", error);
                        return;
                      } finally {
                        setIsLoadingAudio(false);
                      }
                    }

                    // Seek to chapter and play
                    audioRef.current.currentTime = chapter.start_offset_ms / 1000;
                    await audioRef.current.play();
                    setIsPlaying(true);
                  };

                  return (
                    <button
                      key={index}
                      onClick={handleChapterClick}
                      disabled={isLoadingAudio}
                      className="w-full text-left px-3 py-2 rounded-md hover:bg-muted text-sm transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-medium line-clamp-1">
                          {chapter.title}
                        </span>
                        <span className="text-xs text-muted-foreground flex-shrink-0 ml-2">
                          {timeStr}
                        </span>
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>
          ) : null}

          {/* Controls */}
          <div className="flex items-center justify-center gap-4 pt-4">
            <Button size="sm" variant="outline" className="rounded-full">
              <SkipBack className="w-4 h-4" />
            </Button>
            <Button
              size="lg"
              className="rounded-full h-14 w-14"
              onClick={handlePlay}
              disabled={isLoadingAudio}
            >
              {isLoadingAudio ? (
                <Loader2 className="w-6 h-6 animate-spin" />
              ) : isPlaying ? (
                <Pause className="w-6 h-6" />
              ) : (
                <Play className="w-6 h-6" />
              )}
            </Button>
            <Button size="sm" variant="outline" className="rounded-full">
              <SkipForward className="w-4 h-4" />
            </Button>
            <Button size="sm" variant="outline" className="ml-4">
              <Volume2 className="w-4 h-4 mr-2" />
              Volume
            </Button>
          </div>
        </div>
      </Card>

      {/* More Books */}
      {books.length > 1 && (
        <Card className="p-6 border border-border">
          <div className="flex items-center gap-2 mb-4">
            <List className="w-5 h-5" />
            <h3 className="font-semibold text-lg">Your Library</h3>
          </div>

          <div className="space-y-3">
            {books.slice(1, 4).map((book) => (
              <div
                key={book.asin}
                className="flex items-center justify-between p-3 bg-muted rounded-lg hover:bg-muted/80 transition-colors cursor-pointer"
              >
                <div className="flex items-center gap-3">
                  <Play className="w-4 h-4 text-muted-foreground flex-shrink-0" />
                  <div>
                    <p className="font-medium text-sm">{book.title}</p>
                    <p className="text-xs text-muted-foreground">{book.author}</p>
                  </div>
                </div>
                <span className="text-xs text-muted-foreground">
                  {Math.round(book.runtime_min / 60)}h {book.runtime_min % 60}m
                </span>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Playback Settings */}
      <Card className="p-6 border border-border">
        <h3 className="font-semibold text-lg mb-4">Playback Settings</h3>
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <label className="text-sm font-medium">Playback Speed</label>
            <select className="bg-muted px-3 py-1 rounded text-sm border border-border">
              <option>0.75x</option>
              <option defaultValue="1">1x</option>
              <option>1.25x</option>
              <option>1.5x</option>
            </select>
          </div>
          <div className="flex items-center justify-between">
            <label className="text-sm font-medium">Sleep Timer</label>
            <select className="bg-muted px-3 py-1 rounded text-sm border border-border">
              <option>Off</option>
              <option>5 minutes</option>
              <option>15 minutes</option>
              <option>30 minutes</option>
            </select>
          </div>
        </div>
      </Card>
    </div>
  );
}
