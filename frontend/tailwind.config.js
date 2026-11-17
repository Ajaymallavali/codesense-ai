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
        rose: "#be123c",
        cyber: {
          pitch: "#05070a",
          bg: "#080c14",
          surface: "#0d1320",
          card: "#111827",
          cardHover: "#162032",
          border: "#1b2537",
          borderBright: "#283953",
          neon: "#00ff88",
          emerald: "#10b981",
          emeraldDark: "#059669",
          emeraldLight: "#34d399",
          glow: "rgba(16, 185, 129, 0.2)"
        }
      },
      animation: {
        "fade-in": "fadeIn 0.25s cubic-bezier(0.16, 1, 0.3, 1) forwards",
        "fade-in-up": "fadeInUp 0.35s cubic-bezier(0.16, 1, 0.3, 1) forwards",
        "scale-in": "scaleIn 0.3s cubic-bezier(0.16, 1, 0.3, 1) forwards",
        "page-enter": "pageEnter 0.32s cubic-bezier(0.16, 1, 0.3, 1) forwards",
        "slide-right": "slideRight 0.28s cubic-bezier(0.16, 1, 0.3, 1) forwards",
        "pulse-glow": "pulseGlow 2.5s infinite ease-in-out",
        "glow-pulse-slow": "glowPulseSlow 4s ease-in-out infinite",
        "float": "float 3s ease-in-out infinite",
        "orb-float-1": "orbFloat1 18s ease-in-out infinite",
        "orb-float-2": "orbFloat2 22s ease-in-out infinite reverse",
        "orb-float-3": "orbFloat3 14s ease-in-out infinite",
        "radar-sweep": "radarSweep 3s ease-in-out infinite",
        "shimmer": "shimmer 2s infinite linear",
      },
      keyframes: {
        fadeIn: {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        fadeInUp: {
          "0%": { opacity: "0", transform: "translateY(10px) scale(0.99)" },
          "100%": { opacity: "1", transform: "translateY(0) scale(1)" },
        },
        scaleIn: {
          "0%": { opacity: "0", transform: "scale(0.96)" },
          "100%": { opacity: "1", transform: "scale(1)" },
        },
        pageEnter: {
          "0%": { opacity: "0", transform: "translateY(10px) scale(0.995)" },
          "100%": { opacity: "1", transform: "translateY(0) scale(1)" },
        },
        slideRight: {
          "0%": { opacity: "0", transform: "translateX(-10px)" },
          "100%": { opacity: "1", transform: "translateX(0)" },
        },
        orbFloat1: {
          "0%, 100%": { transform: "translate(0px, 0px) scale(1)" },
          "50%": { transform: "translate(40px, -35px) scale(1.1)" },
        },
        orbFloat2: {
          "0%, 100%": { transform: "translate(0px, 0px) scale(1)" },
          "50%": { transform: "translate(-35px, 30px) scale(0.95)" },
        },
        orbFloat3: {
          "0%, 100%": { transform: "translate(0px, 0px) scale(1)" },
          "50%": { transform: "translate(20px, 25px) scale(1.05)" },
        },
        radarSweep: {
          "0%": { transform: "translateX(-100%)" },
          "100%": { transform: "translateX(250%)" },
        },
        glowPulseSlow: {
          "0%, 100%": { opacity: "0.35" },
          "50%": { opacity: "0.75" },
        },
        pulseGlow: {
          "0%, 100%": {
            boxShadow: "0 0 8px rgba(16, 185, 129, 0.2)",
            borderColor: "rgba(16, 185, 129, 0.3)",
          },
          "50%": {
            boxShadow: "0 0 22px rgba(16, 185, 129, 0.55)",
            borderColor: "rgba(0, 255, 136, 0.7)",
          },
        },
        float: {
          "0%, 100%": { transform: "translateY(0)" },
          "50%": { transform: "translateY(-4px)" },
        },
        shimmer: {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
      },
      boxShadow: {
        "neon": "0 0 15px rgba(16, 185, 129, 0.3)",
        "neon-lg": "0 0 25px rgba(0, 255, 136, 0.45)",
        "neon-card": "0 10px 30px -5px rgba(0, 0, 0, 0.7), 0 0 20px rgba(16, 185, 129, 0.2)",
        "cyber": "0 8px 30px rgba(0, 0, 0, 0.6), 0 0 0 1px rgba(27, 37, 55, 0.8)",
      }
    }
  },
  plugins: []
};
