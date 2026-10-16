/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#18212f",
        graphite: "#334155",
        signal: "#0f766e",
        amber: "#d97706",
        rose: "#be123c"
      }
    }
  },
  plugins: []
};
