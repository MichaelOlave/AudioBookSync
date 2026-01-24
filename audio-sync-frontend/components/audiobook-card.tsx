"use client";

import { useState, useRef, useEffect, useCallback, useMemo } from "react";
import { useRouter } from "next/navigation";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Play, Download, Pause, Loader2 } from "lucide-react";
import Image from "next/image";
import { getAPIClient } from "@/lib/api/client";

interface AudiobookCardProps {
  id: string;
  title: string;
  author: string;
  cover: string;
  duration: string;
  narrator: string;
  category: string;
  downloaded?: boolean;
  description?: string;
  rating?: number;
  purchaseDate?: string;
}

export function AudiobookCard({
  id,
  title,
  author,
  cover,
  duration,
  narrator,
  category,
  downloaded = false,
  description,
  rating,
  purchaseDate,
}: AudiobookCardProps) {
  const router = useRouter();
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);
  const [chapters, setChapters] = useState<
    Array<{ start_offset_ms: number; title: string }>
  >([]);
  const [isLoadingChapters, setIsLoadingChapters] = useState(false);
  const audioRef = useRef<HTMLAudioElement>(null);
  const blobUrlRef = useRef<string | null>(null);
  const progressIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const apiClient = useMemo(() => getAPIClient(), []);

  const loadChapters = useCallback(async () => {
    try {
      setIsLoadingChapters(true);
      const chaptersData = (await apiClient.getChapters(id)) as Array<{
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
  }, [id, apiClient]);

  const loadProgress = useCallback(async () => {
    try {
      const progress = (await apiClient.getProgress(id)) as {
        position_ms: number;
      } | null;
      if (progress && audioRef.current) {
        audioRef.current.currentTime = progress.position_ms / 1000;
      }
    } catch (error) {
      console.error("Failed to load progress:", error);
    }
  }, [id, apiClient]);

  const saveProgress = useCallback(async () => {
    if (!audioRef.current) return;

    const duration_ms =
      (audioRef.current.duration || 0) * 1000;
    const position_ms = audioRef.current.currentTime * 1000;
    const percent_complete =
      duration_ms > 0
        ? Math.round((position_ms / duration_ms) * 100)
        : 0;

    try {
      await apiClient.updateProgress(id, {
        position_ms: Math.round(position_ms),
        percent_complete,
        is_finished: percent_complete >= 95,
      });
    } catch (error) {
      console.error("Failed to save progress:", error);
    }
  }, [id, apiClient]);

  // Load progress and chapters when dialog opens
  useEffect(() => {
    if (isDialogOpen) {
      loadProgress();
      loadChapters();
    }
  }, [isDialogOpen, loadProgress, loadChapters]);

  // Setup progress tracking interval
  useEffect(() => {
    if (isPlaying && isDialogOpen) {
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
  }, [isPlaying, isDialogOpen, saveProgress]);

  // Cleanup
  useEffect(() => {
    return () => {
      if (blobUrlRef.current) {
        URL.revokeObjectURL(blobUrlRef.current);
      }
      if (progressIntervalRef.current) {
        clearInterval(progressIntervalRef.current);
      }
      // Save progress on unmount
      if (isDialogOpen) {
        saveProgress();
      }
    };
  }, [isDialogOpen, saveProgress]);

  const handlePlay = async () => {
    if (!audioRef.current) return;

    if (isPlaying) {
      audioRef.current.pause();
      setIsPlaying(false);
      await saveProgress();
    } else {
      try {
        setIsLoading(true);
        const blob = await apiClient.getAudiobook(id);

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
        setIsLoading(false);
      }
    }
  };

  const handleDownload = async () => {
    try {
      setIsDownloading(true);
      const blob = await apiClient.downloadAudiobook(id);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${title}.m4b`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error("Download failed:", error);
    } finally {
      setIsDownloading(false);
    }
  };

  const handleDialogClose = async (open: boolean) => {
    setIsDialogOpen(open);
    if (!open) {
      if (isPlaying) {
        audioRef.current?.pause();
        setIsPlaying(false);
      }
      await saveProgress();
    }
  };

  const handleCardPlay = async () => {
    setIsDialogOpen(true);
    // Trigger play after a brief delay to ensure dialog is open and audio ref is available
    setTimeout(handlePlay, 100);
  };

  const handleCardDownload = async () => {
    await handleDownload();
  };

  return (
    <>
      <Dialog open={isDialogOpen} onOpenChange={handleDialogClose}>
    <Card className="overflow-hidden hover:border-primary/50 transition-all hover:shadow-lg group">
      <div className="relative overflow-hidden bg-muted h-48">
        {cover ? (
          <Image
            src={cover}
            alt={`${title} cover`}
            fill
            className="object-cover w-full h-full"
            sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw"
          />
        ) : (
          <div className="w-full h-full bg-gradient-to-br from-purple-400 to-blue-500 flex items-center justify-center">
            <div className="text-center text-white">
              <div className="text-5xl font-bold mb-2">♪</div>
              <p className="text-sm">{title}</p>
            </div>
          </div>
        )}

        {/* Hover Actions */}
        <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2">
          <Button
            size="sm"
            variant="secondary"
            className="rounded-full"
            onClick={handleCardPlay}
            disabled={isLoading}
          >
            <Play className="w-4 h-4" />
          </Button>
          <Button
            size="sm"
            variant="secondary"
            className="rounded-full"
            onClick={handleCardDownload}
            disabled={isDownloading}
          >
            <Download className="w-4 h-4" />
          </Button>
        </div>

        {/* Status Badge */}
        {downloaded && (
          <Badge className="absolute top-2 right-2 bg-green-600">
            Downloaded
          </Badge>
        )}
      </div>

      <div className="p-4 space-y-3">
        <div className="space-y-1">
          <h3 className="font-semibold truncate text-sm line-clamp-2">
            {title}
          </h3>
          <p className="text-xs text-muted-foreground truncate">{author}</p>
          <p className="text-xs text-muted-foreground">Narrator: {narrator}</p>
        </div>

        <div className="flex items-center justify-between pt-2">
          <Badge variant="outline" className="text-xs">
            {category}
          </Badge>
          <span className="text-xs text-muted-foreground">{duration}</span>
        </div>

        <Button
          className="w-full"
          size="sm"
          variant="outline"
          onClick={() => setIsDialogOpen(true)}
        >
          View Details
        </Button>
      </div>
      </Card>

      <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>
            by {author}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* Cover Image */}
          {cover && (
            <div className="flex justify-center">
              <div className="relative w-48 h-64">
                <Image
                  src={cover}
                  alt={`${title} cover`}
                  fill
                  className="object-cover rounded-lg"
                />
              </div>
            </div>
          )}

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
              <div className="max-h-48 overflow-y-auto space-y-2">
                {chapters.map((chapter, index) => {
                  const hours = Math.floor(chapter.start_offset_ms / 3600000);
                  const minutes = Math.floor(
                    (chapter.start_offset_ms % 3600000) / 60000
                  );
                  const timeStr = `${hours}:${minutes.toString().padStart(2, "0")}`;

                  const handleChapterClick = async () => {
                    if (!audioRef.current) return;

                    // If audio isn't loaded yet, load it first
                    if (!audioRef.current.src) {
                      try {
                        setIsLoading(true);
                        const blob = await apiClient.getAudiobook(id);

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
                        setIsLoading(false);
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
                      disabled={isLoading}
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

          {/* Description */}
          {description && (
            <div className="space-y-2">
              <h3 className="font-semibold text-sm">Description</h3>
              <p className="text-sm text-muted-foreground leading-relaxed">
                {description}
              </p>
            </div>
          )}

          {/* Details Grid */}
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <p className="font-semibold text-muted-foreground">Narrator</p>
              <p>{narrator}</p>
            </div>
            <div>
              <p className="font-semibold text-muted-foreground">Duration</p>
              <p>{duration}</p>
            </div>
            <div>
              <p className="font-semibold text-muted-foreground">Category</p>
              <p>{category}</p>
            </div>
            <div>
              <p className="font-semibold text-muted-foreground">ASIN</p>
              <p className="font-mono text-xs">{id}</p>
            </div>
            {rating !== undefined && (
              <div>
                <p className="font-semibold text-muted-foreground">Rating</p>
                <p>{rating.toFixed(1)} / 5</p>
              </div>
            )}
            {purchaseDate && (
              <div>
                <p className="font-semibold text-muted-foreground">Purchased</p>
                <p>{new Date(purchaseDate).toLocaleDateString()}</p>
              </div>
            )}
          </div>

          {/* Status Badge */}
          {downloaded && (
            <div className="flex items-center gap-2">
              <Badge className="bg-green-600">Downloaded</Badge>
            </div>
          )}

          {/* Actions */}
          <div className="flex flex-col gap-2 pt-4">
            <div className="flex gap-2">
              <Button
                className="flex-1"
                onClick={handlePlay}
                disabled={isLoading || isDownloading}
              >
                {isLoading ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Loading...
                  </>
                ) : isPlaying ? (
                  <>
                    <Pause className="w-4 h-4 mr-2" />
                    Pause
                  </>
                ) : (
                  <>
                    <Play className="w-4 h-4 mr-2" />
                    Play
                  </>
                )}
              </Button>
              <Button
                variant="outline"
                className="flex-1"
                onClick={handleDownload}
                disabled={isLoading || isDownloading}
              >
                <Download className="w-4 h-4 mr-2" />
                {isDownloading ? "Downloading..." : "Download"}
              </Button>
            </div>
            <Button
              variant="outline"
              className="w-full"
              onClick={() => router.push(`/dashboard/now-playing?asin=${id}`)}
            >
              Play Now (Full Page)
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
    </>
  );
}
