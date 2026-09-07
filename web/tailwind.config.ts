import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // Design System: Dark IoT Dashboard
        background: "#0F172A", // Slate 900
        card: "#1E293B",       // Slate 800
        border: "#334155",     // Slate 700

        // Status Colors
        "status-available": "#22C55E", // Green 500
        "status-occupied": "#EF4444",  // Red 500
        "status-reserved": "#F59E0B",  // Amber 500
        "status-unknown": "#64748B",   // Slate 500

        // Text
        foreground: "#F8FAFC",
        muted: "#94A3B8",
      },
      fontFamily: {
        sans: ['var(--font-inter)', 'system-ui', 'sans-serif'],
        mono: ['var(--font-jetbrains)', 'monospace'],
      },
      animation: {
        "pulse-available": "pulse-available 2s cubic-bezier(0.4, 0, 0.6, 1) infinite",
      },
      keyframes: {
        "pulse-available": {
          "0%, 100%": {
            opacity: "1",
            boxShadow: "0 0 0 0 rgba(34, 197, 94, 0.7)",
          },
          "50%": {
            opacity: "0.8",
            boxShadow: "0 0 0 10px rgba(34, 197, 94, 0)",
          },
        },
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};
export default config;