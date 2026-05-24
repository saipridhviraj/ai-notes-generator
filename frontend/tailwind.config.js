/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        chat: {
          sidebar: "#171717",
          main: "#212121",
          surface: "#2f2f2f",
          elevated: "#383838",
          border: "rgba(255,255,255,0.08)",
          muted: "#9b9b9b",
          accent: "#10a37f",
          "accent-hover": "#0d8c6d",
        },
      },
      fontFamily: {
        sans: [
          "Söhne",
          "ui-sans-serif",
          "system-ui",
          "-apple-system",
          "Segoe UI",
          "Roboto",
          "Helvetica Neue",
          "Arial",
          "sans-serif",
        ],
      },
      boxShadow: {
        chat: "0 0 0 1px rgba(255,255,255,0.06), 0 4px 24px rgba(0,0,0,0.25)",
      },
    },
  },
  plugins: [],
};
