import type { Config } from 'tailwindcss'

/** Design tokens live as CSS variables in src/index.css; Tailwind exposes them as semantic utilities. */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        app: 'rgb(var(--c-app) / <alpha-value>)',
        sidebar: 'rgb(var(--c-sidebar) / <alpha-value>)',
        surface: 'rgb(var(--c-surface) / <alpha-value>)',
        fg: 'rgb(var(--c-fg) / <alpha-value>)',
        'fg-2': 'rgb(var(--c-fg-2) / <alpha-value>)',
        'fg-3': 'rgb(var(--c-fg-3) / <alpha-value>)',
        placeholder: 'rgb(var(--c-placeholder) / <alpha-value>)',
        line: 'rgb(var(--c-line) / <alpha-value>)',
        'line-strong': 'rgb(var(--c-line-strong) / <alpha-value>)',
        'line-sidebar': 'rgb(var(--c-line-sidebar) / <alpha-value>)',
        hover: 'rgb(var(--c-hover) / <alpha-value>)',
        'hover-nav': 'rgb(var(--c-hover-nav) / <alpha-value>)',
        'active-nav': 'rgb(var(--c-active-nav) / <alpha-value>)',
        primary: 'rgb(var(--c-primary) / <alpha-value>)',
        'primary-hover': 'rgb(var(--c-primary-hover) / <alpha-value>)',
        'primary-active': 'rgb(var(--c-primary-active) / <alpha-value>)',
        'disabled-bg': 'rgb(var(--c-disabled-bg) / <alpha-value>)',
        'disabled-fg': 'rgb(var(--c-disabled-fg) / <alpha-value>)',
      },
      borderRadius: { control: '0.75rem', card: '1rem' },
      boxShadow: { soft: 'var(--shadow-soft)', composer: 'var(--shadow-composer)' },
      transitionDuration: { fast: '150ms', base: '200ms' },
      fontFamily: { sans: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'] },
      keyframes: {
        'fade-in': { from: { opacity: '0' }, to: { opacity: '1' } },
        'fade-up': { from: { opacity: '0', transform: 'translateY(6px)' }, to: { opacity: '1', transform: 'none' } },
      },
      animation: {
        'fade-in': 'fade-in 200ms ease-out both',
        'fade-up': 'fade-up 240ms ease-out both',
      },
    },
  },
  plugins: [],
} satisfies Config
