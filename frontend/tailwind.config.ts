import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: "#0D1623",
        surface: {
          DEFAULT: "#152236",
          2: "#1C2D44",
          3: "#233555",
        },
        bdr: "#263450",
        accent: {
          DEFAULT: "#D97706",
          muted: "#92400E",
          light: "#FEF3C7",
        },
        ink: {
          DEFAULT: "#E2E8F0",
          2: "#94A3B8",
          3: "#64748B",
        },
        success: "#10B981",
        danger: "#EF4444",
        warning: "#F59E0B",
        platform: {
          twitter: "#1D9BF0",
          telegram: "#2AABEE",
          reddit: "#FF4500",
          youtube: "#FF0000",
          instagram: "#E1306C",
          facebook: "#1877F2",
        },
      },
      fontFamily: {
        sans: ["var(--font-geist-sans)", "system-ui", "sans-serif"],
        mono: ["var(--font-geist-mono)", "monospace"],
      },
      borderRadius: {
        DEFAULT: "6px",
      },
    },
  },
  plugins: [],
};

export default config;
