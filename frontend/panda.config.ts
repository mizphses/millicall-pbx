import { defineConfig } from "@pandacss/dev";

export default defineConfig({
  preflight: true,
  include: ["./src/**/*.{js,jsx,ts,tsx}"],
  exclude: [],
  jsxFramework: "react",
  theme: {
    tokens: {
      colors: {
        ink: { value: "#1b1b1f" },
        "ink.sub": { value: "#4a4a52" },
        "ink.faint": { value: "#8e8e96" },
        bg: { value: "#f0eeeb" },
        "bg.card": { value: "#ffffff" },
        "bg.muted": { value: "#e6e4e0" },
        border: { value: "#d4d2cd" },
        "border.light": { value: "#e6e4e0" },
        accent: { value: "#c45d2c" },
        "accent.hover": { value: "#a84e24" },
        "accent.pale": { value: "#fdf3ee" },
        "nav.bg": { value: "#262630" },
        "nav.ink": { value: "#b0afc0" },
        "nav.active": { value: "#ffffff" },
        green: { value: "#2a7e4f" },
        "green.bg": { value: "#e3f4eb" },
        red: { value: "#b83232" },
        "red.bg": { value: "#fce8e8" },
        info: { value: "#365a8a" },
        "info.bg": { value: "#e5ecf5" },
      },
      fonts: {
        body: { value: "'Noto Sans JP', sans-serif" },
        mono: { value: "'JetBrains Mono', monospace" },
      },
      radii: {
        sm: { value: "3px" },
        md: { value: "5px" },
        lg: { value: "6px" },
        xl: { value: "8px" },
      },
    },
  },
  outdir: "styled-system",
});
