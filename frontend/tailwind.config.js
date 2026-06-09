/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        // Inter (loaded in index.html) with a system fallback stack.
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
        // font-mono keeps Tailwind's default system monospace stack.
      },
    },
  },
  plugins: [],
};
