import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        indago: {
          dark: "#0a0e1a",
          navy: "#0d1526",
          blue: "#0066cc",
          accent: "#00a8ff",
          muted: "#1e2d4a",
          border: "#1e3a5f",
          text: "#94a3b8",
          light: "#e2e8f0",
        },
        forensic: {
          green: "#16a34a",
          red: "#dc2626",
          amber: "#d97706",
          purple: "#7c3aed",
        },
      },
      fontFamily: {
        mono: ["JetBrains Mono", "Courier New", "monospace"],
      },
      backgroundImage: {
        "grid-pattern":
          "radial-gradient(circle at 1px 1px, rgba(0,168,255,0.08) 1px, transparent 0)",
        "hero-gradient":
          "linear-gradient(135deg, #0a0e1a 0%, #0d1526 50%, #0a1628 100%)",
      },
      animation: {
        "pulse-slow": "pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        "scan": "scan 2s linear infinite",
      },
      keyframes: {
        scan: {
          "0%": { transform: "translateY(-100%)", opacity: "0" },
          "50%": { opacity: "1" },
          "100%": { transform: "translateY(100%)", opacity: "0" },
        },
      },
    },
  },
  plugins: [],
};
export default config;
