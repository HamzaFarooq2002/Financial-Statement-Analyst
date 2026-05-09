/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#18211f",
        muted: "#60716c",
        canvas: "#f7f8f5",
        line: "#dbe3de",
        mint: "#2aa876",
        aqua: "#22a7a5",
        coral: "#e25f4f",
        amber: "#d89614",
        violet: "#6b5bd6",
      },
      boxShadow: {
        soft: "0 18px 45px rgba(24, 33, 31, 0.08)",
      },
      fontFamily: {
        sans: [
          "Inter",
          "ui-sans-serif",
          "system-ui",
          "-apple-system",
          "BlinkMacSystemFont",
          "Segoe UI",
          "sans-serif",
        ],
      },
    },
  },
  plugins: [],
};
