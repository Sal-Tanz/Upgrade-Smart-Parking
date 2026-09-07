/**
 * Bottom Navigation Bar for mobile
 * UX Guidelines referenced:
 * - Touch Target Size: min 44x44px (line 22)
 * - Touch Spacing: min 8px gap (line 23)
 * - Readable Font Size: min 16px (line 67)
 * - Mobile First: default mobile + md: lg: xl: breakpoints (line 64)
 */

"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { LayoutDashboard, Car, Bell, Plus } from "lucide-react";

const mobileNavItems = [
  { name: "Home", href: "/", icon: LayoutDashboard },
  { name: "Vehicles", href: "/vehicles", icon: Car },
  { name: "Events", href: "/events", icon: Bell },
];

export function BottomNav() {
  const pathname = usePathname();

  // Hide on desktop
  return (
    <nav className="fixed bottom-0 left-0 right-0 z-40 border-t border-border bg-card/95 backdrop-blur-sm md:hidden">
      <div className="flex items-center justify-around px-2 py-2 safe-area-bottom">
        {mobileNavItems.map((item) => {
          const isActive = pathname === item.href || (item.href !== "/" && pathname.startsWith(item.href));
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex flex-col items-center justify-center gap-1 rounded-lg px-3 py-2 min-h-[44px] min-w-[44px] transition-colors cursor-pointer touch-action-manipulation",
                "hover:bg-accent/10",
                isActive ? "text-accent" : "text-muted-foreground hover:text-foreground"
              )}
            >
              <item.icon className="h-5 w-5" />
              <span className="text-xs font-medium">{item.name}</span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
}

/**
 * Floating Action Button for quick actions on mobile
 * UX Guidelines referenced:
 * - Touch Target Size: min 44x44px (line 22)
 * - Duration Timing: 150-300ms (line 8)
 */
export function FloatingActionButton({ onClick, icon: Icon = Plus }: { onClick: () => void; icon?: typeof Plus }) {
  return (
    <button
      onClick={onClick}
      className="fixed bottom-20 right-4 z-50 flex h-14 w-14 items-center justify-center rounded-full bg-accent text-accent-foreground shadow-lg transition-transform duration-200 hover:scale-105 active:scale-95 cursor-pointer touch-action-manipulation md:hidden"
      aria-label="Quick action"
    >
      <Icon className="h-6 w-6" />
    </button>
  );
}

/**
 * Safe area bottom padding for iOS notch devices
 */
export function SafeAreaPadding() {
  return (
    <div className="h-[env(safe-area-inset-bottom,0px)] md:hidden" />
  );
}