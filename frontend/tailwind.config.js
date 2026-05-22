/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,jsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: '#2E86AB',
        secondary: '#A23B72',
        success: '#28a745',
        danger: '#dc3545',
        warning: '#ffc107',
      },
    },
  },
  plugins: [],
}
