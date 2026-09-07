"use client";

import { Sidebar } from "./sidebar";
import { Header } from "./header";
import { BottomNav } from "./bottom-nav";
import { ErrorBoundary } from "@/components/ui/error-boundary";

interface DashboardShellProps {
  children: React.ReactNode;
  title: string;
  subtitle?: string;
  connectionStatus?: "connected" | "disconnected" | "connecting" | "error";
  onSearch?: (query: string) => void;
}

export function DashboardShell({
  children,
  title,
  subtitle,
  connectionStatus = "connected",
  onSearch,
}: DashboardShellProps) {
  return (
    <div className="flex h-screen bg-background text-foreground">
      <Sidebar />
      <div className="flex flex-1 flex-col overflow-hidden">
        <Header
          title={title}
          subtitle={subtitle}
          connectionStatus={connectionStatus}
          onSearch={onSearch}
        />
        <main className="flex-1 overflow-y-auto p-6 pb-24 md:pb-6">
          <ErrorBoundary>
            {children}
          </ErrorBoundary>
        </main>
        <BottomNav />
      </div>
    </div>
  );
}
