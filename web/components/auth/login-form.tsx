"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter } from "next/navigation";
import { loginSchema, LoginFormData } from "@/lib/validators";
import { AlertCircle } from "lucide-react";

export function LoginForm() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
  });

  async function onSubmit(data: LoginFormData) {
    setError(null);
    try {
      const res = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          username: data.username,
          password: data.password,
        }),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => null);
        setError(errData?.detail || "Invalid username or password");
        return;
      }

      const resData = await res.json();
      if (resData.access_token) {
        localStorage.setItem("auth_token", resData.access_token);
        localStorage.setItem("auth_user", JSON.stringify({
          username: data.username,
          role: resData.role || "admin",
        }));
        router.push("/");
      } else {
        setError("Login failed: no token received");
      }
    } catch (err: any) {
      setError(err?.message || "Failed to connect to server");
    }
  }

  return (
    <div className="rounded-lg border border-border bg-card p-6">
      <h2 className="mb-4 text-xl font-bold text-foreground">Sign In</h2>

      {error && (
        <div className="mb-4 flex items-center gap-2 rounded-lg bg-red-500/10 p-3 text-sm text-red-400">
          <AlertCircle className="h-4 w-4" />
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <div className="space-y-2">
          <label htmlFor="username" className="text-sm font-medium text-foreground">
            Username
          </label>
          <input
            id="username"
            type="text"
            {...register("username")}
            className="w-full rounded-md border border-border bg-background px-3 py-2 text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-accent"
            placeholder="admin"
          />
          {errors.username && (
            <p className="text-xs text-red-400">{errors.username.message}</p>
          )}
        </div>

        <div className="space-y-2">
          <label htmlFor="password" className="text-sm font-medium text-foreground">
            Password
          </label>
          <input
            id="password"
            type="password"
            {...register("password")}
            className="w-full rounded-md border border-border bg-background px-3 py-2 text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-accent"
            placeholder="••••••"
          />
          {errors.password && (
            <p className="text-xs text-red-400">{errors.password.message}</p>
          )}
        </div>

        <button
          type="submit"
          disabled={isSubmitting}
          className="w-full rounded-md bg-accent px-4 py-2 font-medium text-accent-foreground transition-colors hover:bg-accent/90 disabled:opacity-50"
        >
          {isSubmitting ? "Signing in..." : "Sign In"}
        </button>
      </form>
    </div>
  );
}