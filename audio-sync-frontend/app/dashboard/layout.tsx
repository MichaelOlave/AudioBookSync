"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarProvider,
} from "@/components/ui/sidebar";
import { Button } from "@/components/ui/button";
import {
  BookOpen,
  DownloadCloud,
  Settings,
  LogOut,
  Home,
  Music,
  Cloud,
  Clock,
} from "lucide-react";
import { useAuth } from "@/hooks/use-auth";
import { ProtectedRoute } from "@/components/protected-route";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const { logout } = useAuth();

  const menuItems = [
    {
      title: "Home",
      icon: Home,
      href: "/dashboard",
    },
    {
      title: "Library",
      icon: BookOpen,
      href: "/dashboard/library",
    },
    {
      title: "Audible Library",
      icon: Cloud,
      href: "/dashboard/audible",
    },
    {
      title: "Now Playing",
      icon: Music,
      href: "/dashboard/now-playing",
    },
    {
      title: "Downloads",
      icon: DownloadCloud,
      href: "/dashboard/downloads",
    },
    {
      title: "Schedules",
      icon: Clock,
      href: "/dashboard/schedules",
    },
    {
      title: "Settings",
      icon: Settings,
      href: "/dashboard/settings",
    },
  ];

  const isActive = (href: string) => pathname === href;

  return (
    <ProtectedRoute>
      <SidebarProvider>
        <div className="flex h-screen bg-background">
          <Sidebar>
            <SidebarHeader className="border-b">
              <Link
                href="/dashboard"
                className="flex items-center gap-2 px-4 py-2"
              >
                <BookOpen className="w-6 h-6 text-primary" />
                <span className="text-lg font-bold text-primary">
                  AudioSync
                </span>
              </Link>
            </SidebarHeader>

            <SidebarContent>
              <SidebarMenu>
                {menuItems.map((item) => {
                  const Icon = item.icon;
                  return (
                    <SidebarMenuItem key={item.href}>
                      <SidebarMenuButton
                        asChild
                        isActive={isActive(item.href)}
                        className={isActive(item.href) ? "bg-accent" : ""}
                      >
                        <Link
                          href={item.href}
                          className="flex items-center gap-2"
                        >
                          <Icon className="w-4 h-4" />
                          <span>{item.title}</span>
                        </Link>
                      </SidebarMenuButton>
                    </SidebarMenuItem>
                  );
                })}
              </SidebarMenu>
            </SidebarContent>

            <SidebarFooter className="border-t p-4">
              <Button
                variant="ghost"
                className="w-full justify-start text-red-600 hover:bg-red-50 dark:hover:bg-red-950"
                onClick={logout}
              >
                <LogOut className="w-4 h-4 mr-2" />
                Sign Out
              </Button>
            </SidebarFooter>
          </Sidebar>

          <main className="flex-1 overflow-auto">
            <div className="p-8">{children}</div>
          </main>
        </div>
      </SidebarProvider>
    </ProtectedRoute>
  );
}
