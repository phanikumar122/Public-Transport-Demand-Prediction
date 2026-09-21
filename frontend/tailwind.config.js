/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Outfit"', '"Plus Jakarta Sans"', '-apple-system', 'BlinkMacSystemFont', 'sans-serif'],
        display: ['"Space Grotesk"', '"Outfit"', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
      },
      colors: {
        // User Palette
        crimson: {
          50: '#fef3ee',
          100: '#fee4d8',
          200: '#fdc6b0',
          300: '#fba181',
          400: '#f97346',
          500: '#fb5012', // --crimson-carrot
          600: '#dc3704',
          700: '#b42605',
          800: '#90200b',
          900: '#751c0d',
        },
        neonice: {
          50: '#ebfffe',
          100: '#cdfffd',
          200: '#a1fffa',
          300: '#60fef7',
          400: '#1ffdf5',
          500: '#01fdf6', // --neon-ice
          600: '#00d4cf',
          700: '#00a8a5',
          800: '#048381',
          900: '#096c6b',
        },
        periwinkle: {
          50: '#f8f6fc',
          100: '#f1edf9',
          200: '#e3daf4',
          300: '#cbbaed', // --periwinkle
          400: '#af94e2',
          500: '#936dd6',
          600: '#7a51c4',
          700: '#6641a9',
          800: '#54378b',
          900: '#462e71',
        },
        lemon: {
          50: '#fefee8',
          100: '#fdfdc2',
          200: '#faf887',
          300: '#f6ee45',
          400: '#e9df00', // --bright-lemon
          500: '#cfbe00',
          600: '#a69000',
          700: '#7c6500',
          800: '#644e05',
          900: '#554109',
        },
        tropicalmint: {
          50: '#ebfff9',
          100: '#cdffef',
          200: '#a0fedf',
          300: '#5efdc8',
          400: '#1bfcb2',
          500: '#03fcba', // --tropical-mint
          600: '#00d099',
          700: '#00a37b',
          800: '#047f62',
          900: '#076952',
        },
        brand: {
          50: '#fef3ee',
          100: '#fee4d8',
          200: '#fdc6b0',
          300: '#fba181',
          400: '#f97346',
          500: '#fb5012', // Primary
          600: '#dc3704',
          700: '#b42605',
        },
      },
      animation: {
        'pulse-slow': 'pulse 4s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'float': 'float 6s ease-in-out infinite',
      },
      keyframes: {
        float: {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-8px)' },
        }
      }
    },
  },
  plugins: [],
}
