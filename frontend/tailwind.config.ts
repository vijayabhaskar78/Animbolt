import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        amber: {
          DEFAULT: "#F59E0B",
          dim: "rgba(245,158,11,0.12)",
          glow: "rgba(245,158,11,0.25)",
        },
        studio: {
          bg: "#09090A",
          surface: "#0F1011",
          card: "#141516",
          hover: "#191B1D",
          border: "#1E2022",
          mid: "#282B2F",
          text: "#EAEBED",
          muted: "#767980",
          faint: "#3D4047",
        },
      },
      fontFamily: {
        display: ["var(--font-syne)", "system-ui", "sans-serif"],
        sans: ["var(--font-dm-sans)", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "monospace"],
      },
      animation: {
        "fade-up": "fadeUp 0.5s ease forwards",
        "fade-in": "fadeIn 0.4s ease forwards",
        "pulse-amber": "pulseAmber 2s ease-in-out infinite",
        "spin-slow": "spin 3s linear infinite",
      },
      keyframes: {
        fadeUp: {
          "0%": { opacity: "0", transform: "translateY(16px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        fadeIn: {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        pulseAmber: {
          "0%, 100%": { boxShadow: "0 0 0 0 rgba(245,158,11,0)" },
          "50%": { boxShadow: "0 0 20px 4px rgba(245,158,11,0.2)" },
        },
      },
    },
  },
  plugins: [],
};

export default config;
