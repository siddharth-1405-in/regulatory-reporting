import type { Config } from "tailwindcss";

// Uniqus design tokens — mirrored from design_handoff_auditor_cockpit/colors_and_type.css
const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        uq: {
          purple: "#492079",
          magenta: "#B31E7C",
          "dark-purple": "#3B2162",
          lavender: "#A28BBD",
          mauve: "#C879AB",
          "light-lavender": "#E1D9EB",
          blush: "#EED8E6",
          "near-white": "#FAFAFA",
          "alt-light": "#F5F0FA",
          canvas: "#FBF9FD",
          border: "#ECE4F2",
          "border-2": "#F0E8F6",
          ink: "#333333",
          mid: "#555555",
          muted: "#666666",
        },
        ok: "#1F8A5B",
        warn: "#E5A82C",
        warn2: "#E27A2A",
        crit: "#C03A3A",
      },
      fontFamily: {
        display: ["Montserrat", "Arial Black", "sans-serif"],
        body: ["Inter", "system-ui", "sans-serif"],
        mono: ["ui-monospace", "SF Mono", "Menlo", "monospace"],
      },
      borderRadius: { card: "14px", pill: "999px", row: "10px", chip: "9px" },
      boxShadow: {
        card: "0 1px 3px rgba(73,32,121,.06), 0 8px 20px rgba(73,32,121,.04)",
        soft: "0 1px 2px rgba(73,32,121,.08)",
      },
      backgroundImage: {
        "uq-bar": "linear-gradient(90deg,#3B2162 0%,#492079 35%,#B31E7C 70%,#C879AB 100%)",
        "uq-symbol": "linear-gradient(135deg,#3B2162 0%,#492079 50%,#B31E7C 100%)",
        "uq-conf": "linear-gradient(90deg,#492079,#B31E7C)",
      },
    },
  },
  plugins: [],
};
export default config;
