/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          950: "#101418",
          800: "#242c34",
          600: "#4c5967",
          400: "#8793a0",
          100: "#eef2f5",
        },
      },
      boxShadow: {
        soft: "0 1px 2px rgba(16, 20, 24, 0.06), 0 8px 24px rgba(16, 20, 24, 0.04)",
      },
    },
  },
  plugins: [],
};

