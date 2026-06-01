import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        background: "#08111f",
        foreground: "#f8fafc",
        muted: "#94a3b8",
        border: "rgba(148, 163, 184, 0.2)",
        card: "#0f172a",
        panel: "#0b1220",
        elevated: "#111c2e",
        brand: "#2563eb",
        primary: "#2563eb",
        navy: "#0f2742",
        slate: "#334155",
        success: "#22c55e",
        warning: "#f59e0b",
        critical: "#ef4444",
        info: "#38bdf8",
        cyan: "#38bdf8",
        violet: "#6366f1",
        ink: "#eef2ff",
        line: "rgba(148, 163, 184, 0.18)",
        surface: "#101827",
        riskHigh: "#ef4444",
        riskMedium: "#f59e0b",
        riskLow: "#22c55e",
      },
      boxShadow: {
        glow: "0 14px 34px rgba(37, 99, 235, 0.18)",
        panel: "0 18px 45px rgba(2, 6, 23, 0.28)",
      },
      backgroundImage: {
        "app-radial": "linear-gradient(180deg, #08111f 0%, #0b1220 48%, #0f172a 100%)",
        "glass-line": "linear-gradient(135deg, rgba(148,163,184,0.15), rgba(148,163,184,0.04))",
      },
    },
  },
  plugins: [],
};

export default config;
