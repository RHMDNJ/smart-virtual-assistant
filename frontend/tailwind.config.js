/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  darkMode: "media",
  theme: {
    extend: {
      colors: {
        // Dipetakan ke CSS variable di index.css agar mode gelap cukup
        // mengganti nilai variabelnya, bukan kelas di setiap komponen.
        surface: "rgb(var(--surface) / <alpha-value>)",
        raised: "rgb(var(--raised) / <alpha-value>)",
        line: "rgb(var(--line) / <alpha-value>)",
        ink: "rgb(var(--ink) / <alpha-value>)",
        muted: "rgb(var(--muted) / <alpha-value>)",
        brand: "rgb(var(--brand) / <alpha-value>)",
        "brand-ink": "rgb(var(--brand-ink) / <alpha-value>)",
      },
      keyframes: {
        "fade-up": {
          from: { opacity: "0", transform: "translateY(6px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        "fade-in": { from: { opacity: "0" }, to: { opacity: "1" } },
        "scale-in": {
          from: { opacity: "0", transform: "scale(.96)" },
          to: { opacity: "1", transform: "scale(1)" },
        },
        "slide-up": {
          from: { opacity: "0", transform: "translateY(8px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        "dot-bounce": {
          "0%, 80%, 100%": { transform: "translateY(0)", opacity: ".45" },
          "40%": { transform: "translateY(-4px)", opacity: "1" },
        },
        "caret-blink": { "0%, 100%": { opacity: "1" }, "50%": { opacity: "0" } },
        "pulse-ring": {
          "0%": { transform: "scale(.9)", opacity: ".7" },
          "70%": { transform: "scale(1.8)", opacity: "0" },
          "100%": { opacity: "0" },
        },
        shake: {
          "0%, 100%": { transform: "translateX(0)" },
          "25%": { transform: "translateX(-4px)" },
          "75%": { transform: "translateX(4px)" },
        },
      },
      animation: {
        "fade-up": "fade-up .28s cubic-bezier(.22,.8,.3,1) both",
        "fade-in": "fade-in .2s ease-out both",
        "scale-in": "scale-in .32s cubic-bezier(.22,.8,.3,1) both",
        "slide-up": "slide-up .22s cubic-bezier(.22,.8,.3,1) both",
        "dot-bounce": "dot-bounce 1.2s ease-in-out infinite",
        "caret-blink": "caret-blink 1s step-end infinite",
        "pulse-ring": "pulse-ring 2s cubic-bezier(.2,.6,.4,1) infinite",
        shake: "shake .3s ease-in-out",
      },
    },
  },
  plugins: [],
};
