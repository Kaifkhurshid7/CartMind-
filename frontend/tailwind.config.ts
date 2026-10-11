import type { Config } from 'tailwindcss'

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        ink: { 950: '#0b1020', 900: '#111830', 800: '#182243', 700: '#243257' },
        brand: { 400: '#7c9cff', 500: '#5b7cfa', 600: '#4563e6' },
      },
      fontFamily: { sans: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'] },
    },
  },
  plugins: [],
} satisfies Config
