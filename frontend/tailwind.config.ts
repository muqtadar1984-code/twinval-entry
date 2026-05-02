import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: "#1B4F72",
          50: "#EAF1F8",
          100: "#D4E2F0",
          600: "#1B4F72",
          700: "#163E5A",
          900: "#0E2A3D",
        },
        accent: {
          DEFAULT: "#2ECC71",
          50: "#E9F9F0",
          600: "#2ECC71",
          700: "#27AE60",
        },
        warning: {
          DEFAULT: "#F39C12",
          50: "#FEF3E2",
          600: "#F39C12",
          700: "#D27D04",
        },
        danger: {
          DEFAULT: "#E74C3C",
          50: "#FCEBE9",
          600: "#E74C3C",
          700: "#C0392B",
        },
        surface: "#FFFFFF",
        canvas: "#F4F6F9",
        ink: {
          DEFAULT: "#1F2A37",
          muted: "#5B6776",
          subtle: "#8A95A4",
        },
        border: "#E2E7EE",
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'Segoe UI', 'Roboto', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'monospace'],
      },
      boxShadow: {
        card: "0 1px 2px rgba(15, 23, 42, 0.04), 0 1px 3px rgba(15, 23, 42, 0.06)",
        elevated: "0 4px 6px -1px rgba(15, 23, 42, 0.06), 0 2px 4px -2px rgba(15, 23, 42, 0.05)",
      },
      borderRadius: {
        xl: "0.875rem",
      },
    },
  },
  plugins: [],
} satisfies Config;
