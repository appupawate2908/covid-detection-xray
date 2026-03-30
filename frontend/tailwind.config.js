/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Plus Jakarta Sans"', 'sans-serif'],
        mono: ['"IBM Plex Mono"', 'monospace'],
      },
      colors: {
        bg:      '#f1f5f9',
        surface: '#ffffff',
        border:  '#e2e8f0',
        blue: {
          DEFAULT: '#2563eb',
          dark:    '#1d4ed8',
          mid:     '#3b82f6',
          light:   '#eff6ff',
          border:  '#bfdbfe',
        },
        txt: {
          1: '#0f172a',
          2: '#334155',
          3: '#64748b',
          4: '#94a3b8',
        },
        covid: {
          DEFAULT: '#ef4444',
          dark:    '#dc2626',
          bg:      '#fef2f2',
          border:  '#fecaca',
        },
        normal: {
          DEFAULT: '#16a34a',
          bg:      '#f0fdf4',
          border:  '#bbf7d0',
        },
        pneumo: {
          DEFAULT: '#d97706',
          bg:      '#fffbeb',
          border:  '#fde68a',
        },
        sev: {
          0: '#16a34a',
          1: '#ca8a04',
          2: '#ea580c',
          3: '#dc2626',
        },
      },
      borderRadius: {
        xl:  '12px',
        '2xl': '16px',
        '3xl': '20px',
      },
      boxShadow: {
        card:  '0 1px 3px rgba(0,0,0,0.04), 0 4px 20px rgba(0,0,0,0.06)',
        'card-hover': '0 4px 8px rgba(0,0,0,0.06), 0 12px 32px rgba(0,0,0,0.10)',
        sm: '0 1px 3px rgba(0,0,0,0.06)',
      },
      animation: {
        'fade-up':  'fadeUp  0.4s ease both',
        'zoom-in':  'zoomIn  0.3s ease both',
        'slide-up': 'slideUp 0.4s ease both',
        'fade-in':  'fadeIn  0.3s ease both',
        'spin-slow': 'spin 1.4s linear infinite',
      },
      keyframes: {
        fadeUp:  { from: { opacity: '0', transform: 'translateY(16px)' }, to: { opacity: '1', transform: 'translateY(0)' } },
        zoomIn:  { from: { opacity: '0', transform: 'scale(0.96)' },      to: { opacity: '1', transform: 'scale(1)' } },
        slideUp: { from: { opacity: '0', transform: 'translateY(24px)' }, to: { opacity: '1', transform: 'translateY(0)' } },
        fadeIn:  { from: { opacity: '0' },                                 to: { opacity: '1' } },
      },
    },
  },
  plugins: [require('@tailwindcss/forms')],
}
