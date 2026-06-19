// tailwind.config.js — clawplay v1.1.0 build pipeline
//
// Compiles utility-first CSS from templates/**/*.html so the four report
// templates no longer need a network call to cdn.tailwindcss.com.
//
// Usage:
//     npx tailwindcss -i templates/dist/input.css -o templates/dist/styles.css --minify
//     # or via clawplay-build-assets
//
// The content scan covers all four HTML templates plus the shared
// design tokens in templates/dist/input.css.

module.exports = {
  content: [
    "./templates/**/*.html",
    "./templates/dist/**/*.js",
  ],
  theme: {
    extend: {
      fontFamily: {
        display: ["Georgia", "serif"],
        body: ["Karla", "system-ui", "sans-serif"],
        mono: ['"JetBrains Mono"', "Menlo", "monospace"],
      },
      colors: {
        void: "#0a0a0a",
        surface: "#131313",
        raised: "#1a1a1a",
        dim: "#525252",
        muted: "#a3a3a3",
        blue: {
          deep: "#1e40af",
          DEFAULT: "#2563eb",
          light: "#60a5fa",
        },
        red: {
          DEFAULT: "#dc2626",
          live: "#fb2c36",
        },
      },
      boxShadow: {
        card: "5px 5px 0 #000",
        "card-red": "5px 5px 0 #dc2626",
        "card-blue": "5px 5px 0 #1e40af",
      },
    },
  },
  plugins: [],
};
