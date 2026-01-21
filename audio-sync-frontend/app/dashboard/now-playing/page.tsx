"use client";

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
} from "lucide-react";

export default function NowPlayingPage() {
  const currentBook = {
    title: "The Midnight Library",
    author: "Matt Haig",
    narrator: "Carey Mulligan",
    duration: "9h 26m",
    currentTime: "3h 24m",
    category: "Fiction",
    description:
      "Between life and death there is a library. And within that library, the shelves go on forever. Every book provides a chance to try another life you could have lived.",
  };

  const progressPercent = (3.4 / 9.43) * 100;

  const queueItems = [
    { id: 1, title: "Chapter 5: The Choice", duration: "18m" },
    { id: 2, title: "Chapter 6: Finding Direction", duration: "22m" },
    { id: 3, title: "Chapter 7: The Cost", duration: "19m" },
  ];

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
          {/* Book Cover Placeholder */}
          <div className="w-full h-60 bg-gradient-to-br from-purple-400 to-blue-500 rounded-lg flex items-center justify-center text-white">
            <div className="text-center">
              <div className="text-6xl mb-2">♪</div>
              <p className="text-lg font-semibold">{currentBook.title}</p>
            </div>
          </div>

          {/* Book Info */}
          <div className="space-y-2">
            <h2 className="text-2xl font-bold">{currentBook.title}</h2>
            <p className="text-muted-foreground">by {currentBook.author}</p>
            <div className="flex gap-2 pt-2">
              <Badge variant="outline">{currentBook.category}</Badge>
              <Badge variant="outline">Narrator: {currentBook.narrator}</Badge>
            </div>
            <p className="text-sm text-muted-foreground leading-relaxed pt-4">
              {currentBook.description}
            </p>
          </div>

          {/* Progress Bar */}
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span className="font-medium">{currentBook.currentTime}</span>
              <span className="text-muted-foreground">{currentBook.duration}</span>
            </div>
            <div className="w-full h-2 bg-muted rounded-full overflow-hidden">
              <div
                className="h-full bg-primary transition-all"
                style={{ width: `${progressPercent}%` }}
              />
            </div>
          </div>

          {/* Controls */}
          <div className="flex items-center justify-center gap-4 pt-4">
            <Button size="sm" variant="outline" className="rounded-full">
              <SkipBack className="w-4 h-4" />
            </Button>
            <Button size="lg" className="rounded-full h-14 w-14">
              <Pause className="w-6 h-6" />
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

      {/* Up Next */}
      <Card className="p-6 border border-border">
        <div className="flex items-center gap-2 mb-4">
          <List className="w-5 h-5" />
          <h3 className="font-semibold text-lg">Up Next</h3>
        </div>

        <div className="space-y-3">
          {queueItems.map((item) => (
            <div
              key={item.id}
              className="flex items-center justify-between p-3 bg-muted rounded-lg hover:bg-muted/80 transition-colors cursor-pointer"
            >
              <div className="flex items-center gap-3">
                <Play className="w-4 h-4 text-muted-foreground flex-shrink-0" />
                <div>
                  <p className="font-medium text-sm">{item.title}</p>
                </div>
              </div>
              <span className="text-xs text-muted-foreground">{item.duration}</span>
            </div>
          ))}
        </div>
      </Card>

      {/* Playback Settings */}
      <Card className="p-6 border border-border">
        <h3 className="font-semibold text-lg mb-4">Playback Settings</h3>
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <label className="text-sm font-medium">Playback Speed</label>
            <select className="bg-muted px-3 py-1 rounded text-sm border border-border">
              <option>0.75x</option>
              <option selected>1x</option>
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
