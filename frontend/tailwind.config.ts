import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        background: "#050713",
        foreground: "#f7f8ff",
        muted: "#8f9bb7",
        border: "rgba(148, 163, 184, 0.18)",
        card: "rgba(16, 19, 42, 0.78)",
        panel: "#0a0d1f",
        brand: "#7c3aed",
        cyan: "#38bdf8",
        violet: "#a855f7",
        ink: "#eef2ff",
        line: "rgba(148, 163, 184, 0.18)",
        surface: "#080b1d",
        riskHigh: "#fb7185",
        riskMedium: "#f59e0b",
        riskLow: "#22c55e",
      },
      boxShadow: {
        glow: "0 0 34px rgba(124, 58, 237, 0.28)",
        panel: "0 24px 70px rgba(0, 0, 0, 0.35)",
      },
      backgroundImage: {
        "app-radial": "radial-gradient(circle at 20% 0%, rgba(124,58,237,0.26), transparent 32%), radial-gradient(circle at 80% 20%, rgba(56,189,248,0.14), transparent 28%)",
        "glass-line": "linear-gradient(135deg, rgba(255,255,255,0.16), rgba(255,255,255,0.04))",
      },
    },
  },
  plugins: [],
};

export default config;
