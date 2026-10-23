/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          bg: "#0B0B0B",
          surface: "#151515",
          raised: "#1E1E1E",
          pink: "#FF2DA8",
          pinkHover: "#E91E93",
          chartreuse: "#D4FF3F",
          text: "#FFFFFF",
          muted: "#A7A7A7",
          border: "#282828",
          borderBright: "#3E3E3E"
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace']
      }
    },
  },
  plugins: [],
}
