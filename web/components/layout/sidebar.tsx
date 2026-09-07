"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { signOut, useSession } from "next-auth/react";
import {
  LayoutDashboard,
  Car,
  ParkingSquare,
  Calendar,
  Bell,
  BarChart3,
  LogOut,
} from "lucide-react";
import { cn } from "@/lib/utils";

const navigation = [
  { name: "Dashboard", href: "/", icon: LayoutDashboard },
  { name: "Vehicles", href: "/vehicles", icon: Car },
  { name: "Events", href: "/events", icon: Bell },
  { name: "Attendance", href: "/attendance", icon: Calendar },
  { name: "Reports", href: "/reports", icon: BarChart3 },
];

export function Sidebar() {
  const pathname = usePathname();
  const { data: session } = useSession();

  return (
    <aside className="flex h-screen w-64 flex-col border-r border-border bg-card">
      {/* Logo */}
      <Link href="/" className="flex h-16 items-center gap-2 border-b border-border px-6 cursor-pointer hover:bg-accent/5">
        <ParkingSquare className="h-8 w-8 text-status-available" />
        <div className="flex flex-col">
          <span className="text-lg font-bold text-foreground">Smart Parking</span>
          <span className="text-xs text-muted">IoT Monitoring</span>
        </div>
      </Link>

      {/* Navigation */}
      <nav className="flex-1 space-y-1 px-3 py-4">
        {navigation.map((item) => {
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.name}
              href={item.href}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                "hover:bg-accent/10 hover:text-accent",
                "cursor-pointer",
                isActive
                  ? "bg-accent/20 text-accent"
                  : "text-muted hover:text-foreground"
              )}
            >
              <item.icon className="h-5 w-5" />
              {item.name}
            </Link>
          );
        })}
      </nav>

      {/* Footer with user info and sign out */}
      <div className="border-t border-border p-4">
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-accent/20 text-accent font-semibold">
              {session?.user?.name?.charAt(0).toUpperCase() || "U"}
            </div>
            <div className="flex flex-col">
              <span className="text-sm font-medium text-foreground">
                {session?.user?.name || "User"}
              </span>
              <span className="text-xs text-muted capitalize">
                {session?.user?.role || "viewer"}
              </span>
            </div>
          </div>
          <button
            onClick={() => signOut({ callbackUrl: "/login" })}
            className="rounded-lg p-2 text-muted transition-colors hover:bg-red-500/10 hover:text-red-400 cursor-pointer"
            aria-label="Sign out"
          >
            <LogOut className="h-4 w-4" />
          </button>
        </div>
      </div>
    </aside>
  );
}