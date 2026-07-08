import type { Config } from "tailwindcss"

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Geist", "Inter", "Segoe UI", "Arial", "sans-serif"],
        mono: ["Geist Mono", "Consolas", "monospace"],
      },
      colors: {
        enterprise: {
          blue: "#2563eb",
          green: "#16a34a",
          amber: "#d97706",
          red: "#dc2626",
          slate: "#475569",
        },
      },
      boxShadow: {
        soft: "0 12px 32px -24px rgb(15 23 42 / 0.35)",
      },
    },
  },
}

export default config

