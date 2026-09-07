"use client";

import { useEffect } from "react";
import { Button } from "@/components/ui/button";
import { AlertTriangle } from "lucide-react";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("App Router Error:", error);
  }, [error]);

  return (
    <div className="flex min-h-[500px] flex-col items-center justify-center p-6 text-center">
      <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-red-500/10 text-red-500">
        <AlertTriangle className="h-8 w-8" />
      </div>
      <h2 className="text-xl font-bold text-foreground">Terjadi Kesalahan pada Aplikasi</h2>
      <p className="mt-2 max-w-md text-sm text-muted-foreground">
        {error.message || "An unexpected error occurred while loading this page."}
      </p>
      <div className="mt-6 flex gap-3">
        <Button onClick={() => reset()} variant="default">
          Coba Lagi
        </Button>
        <Button onClick={() => window.location.href = "/"} variant="outline">
          Kembali ke Dashboard
        </Button>
      </div>
    </div>
  );
}
