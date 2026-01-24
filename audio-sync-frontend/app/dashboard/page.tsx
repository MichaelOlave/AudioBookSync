"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { useAuth } from "@/hooks/use-auth";
import { useLibrary } from "@/hooks/use-library";
import { useSync } from "@/hooks/use-sync";
import { useDownloads } from "@/hooks/use-downloads";
import { BookOpen, Download, Music, TrendingUp, Loader2 } from "lucide-react";

export default function DashboardHome() {
  const { user } = useAuth();
  const { books, total, fetchLibrary } = useLibrary();
  const { currentSync, startSync } = useSync();
  const { getDownloads } = useDownloads();
  const [isSyncing, setIsSyncing] = useState(false);

  useEffect(() => {
    // Fetch initial data
    const initData = async () => {
      try {
        await fetchLibrary(1, 50);
        await getDownloads("completed", 1, 10);
      } catch (err) {
        console.error("Failed to fetch initial data:", err);
      }
    };
    initData();
  }, [fetchLibrary, getDownloads]);

  const handleStartSync = async () => {
    try {
      setIsSyncing(true);
      await startSync("full");
    } catch (err) {
      console.error("Failed to start sync:", err);
    } finally {
      setIsSyncing(false);
    }
  };

  const downloadedCount = books.filter((b) => b.is_downloaded).length;
  const decryptedCount = books.filter((b) => b.is_decrypted).length;

  const stats = [
    {
      title: "Books in Library",
      value: total.toString(),
      icon: BookOpen,
      color: "text-blue-600",
    },
    {
      title: "Downloaded",
      value: downloadedCount.toString(),
      icon: Download,
      color: "text-green-600",
    },
    {
      title: "Ready to Play",
      value: decryptedCount.toString(),
      icon: Music,
      color: "text-purple-600",
    },
    {
      title: "Syncing",
      value: currentSync?.status === "in_progress" ? "Yes" : "No",
      icon: TrendingUp,
      color: "text-orange-600",
    },
  ];

  return (
    <div className="space-y-8">
      {/* Welcome Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">
          Welcome back, {user?.username || "User"}!
        </h1>
        <p className="text-muted-foreground mt-2">
          Here&apos;s an overview of your audiobook library
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {stats.map((stat, idx) => {
          const Icon = stat.icon;
          return (
            <Card key={idx} className="p-6 border border-border">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">
                    {stat.title}
                  </p>
                  <p className="text-3xl font-bold mt-2">{stat.value}</p>
                </div>
                <Icon className={`w-8 h-8 ${stat.color} opacity-20`} />
              </div>
            </Card>
          );
        })}
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card className="p-6 border border-border">
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <Download className="w-6 h-6 text-blue-600" />
              <h3 className="font-semibold">Sync Library</h3>
            </div>
            <p className="text-sm text-muted-foreground">
              Download new books from your Audible account and update your
              library
            </p>
            <Button
              className="w-full"
              onClick={handleStartSync}
              disabled={isSyncing || currentSync?.status === "in_progress"}
            >
              {isSyncing || currentSync?.status === "in_progress" ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Syncing...
                </>
              ) : (
                "Start Sync"
              )}
            </Button>
          </div>
        </Card>

        <Card className="p-6 border border-border">
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <BookOpen className="w-6 h-6 text-green-600" />
              <h3 className="font-semibold">View Library</h3>
            </div>
            <p className="text-sm text-muted-foreground">
              Browse and manage all your audiobooks in one place
            </p>
            <Link href="/dashboard/library">
              <Button className="w-full">Browse</Button>
            </Link>
          </div>
        </Card>

        <Card className="p-6 border border-border">
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <Music className="w-6 h-6 text-purple-600" />
              <h3 className="font-semibold">Continue Listening</h3>
            </div>
            <p className="text-sm text-muted-foreground">
              Resume your current audiobook where you left off
            </p>
            <Link href="/dashboard/now-playing">
              <Button className="w-full" variant="outline">
                Resume
              </Button>
            </Link>
          </div>
        </Card>
      </div>

      {/* Recent Activity */}
      <Card className="p-6 border border-border">
        <h3 className="font-semibold mb-4">Recent Activity</h3>
        <div className="space-y-4">
          {[
            {
              title: "The Midnight Library",
              action: "Started listening",
              time: "2 hours ago",
            },
            {
              title: "Project Hail Mary",
              action: "Downloaded",
              time: "Yesterday",
            },
            { title: "Educated", action: "Finished", time: "3 days ago" },
          ].map((activity, idx) => (
            <div
              key={idx}
              className="flex items-center justify-between pb-4 border-b last:border-0 last:pb-0"
            >
              <div className="flex items-center gap-3">
                <BookOpen className="w-4 h-4 text-muted-foreground" />
                <div>
                  <p className="font-medium text-sm">{activity.title}</p>
                  <p className="text-xs text-muted-foreground">
                    {activity.action}
                  </p>
                </div>
              </div>
              <span className="text-xs text-muted-foreground">
                {activity.time}
              </span>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
