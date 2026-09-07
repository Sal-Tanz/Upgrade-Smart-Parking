'use client';

import { Bell, Search } from 'lucide-react';
import { Badge } from '@/components/ui/badge';

interface HeaderProps {
  title: string;
  subtitle?: string;
  connectionStatus?: 'connected' | 'disconnected' | 'connecting' | 'error';
  onSearch?: (query: string) => void;
}

export function Header({ title, subtitle, connectionStatus = 'disconnected', onSearch }: HeaderProps) {
  return (
    <header className="flex items-center justify-between border-b border-border bg-card px-6 py-4">
      {/* Left side: Title */}
      <div>
        <h1 className="text-2xl font-bold text-foreground">{title}</h1>
        {subtitle && <p className="text-sm text-muted-foreground">{subtitle}</p>}
      </div>

      {/* Right side: Search, Connection Status, Notifications */}
      <div className="flex items-center gap-4">
        {/* Search Bar */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search slots, vehicles, events..."
            className="w-64 rounded-md border border-border bg-background pl-10 pr-4 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-accent"
            onChange={(e) => onSearch?.(e.target.value)}
          />
        </div>

        {/* Connection Status Badge */}
        <Badge
          variant={
            connectionStatus === 'connected'
              ? 'default'
              : connectionStatus === 'connecting'
              ? 'secondary'
              : 'destructive'
          }
          className="gap-1"
        >
          <span
            className={`h-2 w-2 rounded-full ${
              connectionStatus === 'connected'
                ? 'bg-status-available animate-pulse-available'
                : connectionStatus === 'connecting'
                ? 'bg-status-reserved animate-pulse'
                : 'bg-status-occupied'
            }`}
          />
          {connectionStatus === 'connected'
            ? 'Live'
            : connectionStatus === 'connecting'
            ? 'Connecting...'
            : 'Offline'}
        </Badge>

        {/* Notifications Bell */}
        <button className="relative rounded-md p-2 text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground">
          <Bell className="h-5 w-5" />
          <span className="absolute -top-1 -right-1 flex h-5 w-5 items-center justify-center rounded-full bg-status-occupied text-xs font-bold text-white">
            3
          </span>
        </button>
      </div>
    </header>
  );
}
