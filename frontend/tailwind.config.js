/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        ups: {
          blue: '#003DA5',
          red: '#E30613',
        },
      },
    },
  },
  plugins: [],
}
