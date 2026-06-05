import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        background: "#090A0F",
        foreground: "#F5F6FA",
        muted: "#94A3B8",
        border: "rgba(148, 163, 184, 0.15)",
        card: "#121420",
        panel: "#121420",
        elevated: "#1A1D2E",
        brand: "#7C4DFF",
        primary: "#7C4DFF",
        navy: "#151830",
        slate: "#334155",
        success: "#00E5FF",
        warning: "#FFB300",
        critical: "#FF1744",
        info: "#00E5FF",
        cyan: "#00E5FF",
        violet: "#7C4DFF",
        ink: "#F5F6FA",
        line: "rgba(124, 77, 255, 0.12)",
        surface: "#0E1018",
        riskHigh: "#FF1744",
        riskMedium: "#FFB300",
        riskLow: "#00E5FF",
      },
      boxShadow: {
        glow: "0 14px 34px rgba(124, 77, 255, 0.22)",
        panel: "0 18px 45px rgba(2, 6, 23, 0.35)",
        "orchid-lift": "0 20px 40px rgba(124, 77, 255, 0.12)",
        "cyan-glow": "0 0 20px rgba(0, 229, 255, 0.25)",
      },
      backgroundImage: {
        "app-radial": "linear-gradient(180deg, #090A0F 0%, #0E1018 48%, #121420 100%)",
        "glass-line": "linear-gradient(135deg, rgba(124,77,255,0.15), rgba(148,163,184,0.04))",
      },
    },
  },
  plugins: [],
};

export default config;
