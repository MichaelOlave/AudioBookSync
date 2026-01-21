"use client";

import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Play, Download, MoreVertical } from "lucide-react";
import Image from "next/image";

interface AudiobookCardProps {
  id: string;
  title: string;
  author: string;
  cover: string;
  duration: string;
  narrator: string;
  category: string;
  downloaded?: boolean;
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
}: AudiobookCardProps) {
  return (
    <Card className="overflow-hidden hover:border-primary/50 transition-all hover:shadow-lg group">
      <div className="relative overflow-hidden bg-muted h-48">
        <div className="w-full h-full bg-gradient-to-br from-purple-400 to-blue-500 flex items-center justify-center">
          <div className="text-center text-white">
            <div className="text-5xl font-bold mb-2">♪</div>
            <p className="text-sm">{title}</p>
          </div>
        </div>

        {/* Hover Actions */}
        <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2">
          <Button size="sm" variant="secondary" className="rounded-full">
            <Play className="w-4 h-4" />
          </Button>
          <Button size="sm" variant="secondary" className="rounded-full">
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

        <Button className="w-full" size="sm" variant="outline">
          View Details
        </Button>
      </div>
    </Card>
  );
}
