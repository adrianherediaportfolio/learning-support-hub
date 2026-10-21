/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: { forest: '#254b43', sage: '#e1ede5', sand: '#f6f5f0', ink: '#20312d' },
    },
  },
  plugins: [],
}
