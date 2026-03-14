import type { Config } from "tailwindcss"

const config = {
  darkMode: ["class"],
  content: [
    './pages/**/*.{ts,tsx}',
    './components/**/*.{ts,tsx}',
    './app/**/*.{ts,tsx}',
    './src/**/*.{ts,tsx}',
  ],
  prefix: "",
  theme: {
  	container: {
  		center: true,
  		padding: {
  			DEFAULT: '1.5rem',
  			sm: '2rem',
  			lg: '3rem',
  		},
  		screens: {
  			sm: '640px',
  			md: '768px',
  			lg: '1024px',
  			xl: '1280px',
  			'2xl': '1600px', // Wider for better space usage
  		}
  	},
  		extend: {
  			fontFamily: {
				display: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'sans-serif'],
				body: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'sans-serif'],
  				mono: ['"IBM Plex Mono"', '"JetBrains Mono"', '"Fira Code"', '"Courier New"', 'monospace'],
  				terminal: ['"IBM Plex Mono"', '"JetBrains Mono"', '"Fira Code"', '"Courier New"', 'monospace'],
  			},
  		colors: {
			border: 'rgb(var(--border-default-rgb) / <alpha-value>)',
			input: 'rgb(var(--border-default-rgb) / <alpha-value>)',
			ring: 'rgb(var(--accent-rgb) / <alpha-value>)',
			background: 'rgb(var(--bg-base-rgb) / <alpha-value>)',
			foreground: 'rgb(var(--text-primary-rgb) / <alpha-value>)',
  			primary: {
				DEFAULT: 'rgb(var(--accent-rgb) / <alpha-value>)',
				foreground: '#ffffff'
  			},
  			secondary: {
				DEFAULT: 'rgb(var(--bg-surface-2-rgb) / <alpha-value>)',
				foreground: 'rgb(var(--text-primary-rgb) / <alpha-value>)'
  			},
  			destructive: {
				DEFAULT: 'rgb(var(--negative-rgb) / <alpha-value>)',
				foreground: '#ffffff'
  			},
  			muted: {
				DEFAULT: 'rgb(var(--bg-surface-2-rgb) / <alpha-value>)',
				foreground: 'rgb(var(--text-secondary-rgb) / <alpha-value>)'
  			},
  			accent: {
				DEFAULT: 'rgb(var(--accent-rgb) / <alpha-value>)',
				foreground: '#ffffff'
  			},
  			popover: {
				DEFAULT: 'rgb(var(--bg-surface-1-rgb) / <alpha-value>)',
				foreground: 'rgb(var(--text-primary-rgb) / <alpha-value>)'
  			},
  			card: {
				DEFAULT: 'rgb(var(--bg-surface-1-rgb) / <alpha-value>)',
				foreground: 'rgb(var(--text-primary-rgb) / <alpha-value>)'
  			},
			positive: {
				DEFAULT: 'rgb(var(--positive-rgb) / <alpha-value>)',
				bg: 'var(--positive-bg)'
			},
			negative: {
				DEFAULT: 'rgb(var(--negative-rgb) / <alpha-value>)',
				bg: 'var(--negative-bg)'
			},
			neutral: 'rgb(var(--neutral-rgb) / <alpha-value>)',
			text: {
				primary: 'rgb(var(--text-primary-rgb) / <alpha-value>)',
				secondary: 'rgb(var(--text-secondary-rgb) / <alpha-value>)',
				tertiary: 'rgb(var(--text-tertiary-rgb) / <alpha-value>)',
			},
			surface: {
				1: 'rgb(var(--bg-surface-1-rgb) / <alpha-value>)',
				2: 'rgb(var(--bg-surface-2-rgb) / <alpha-value>)',
				3: 'rgb(var(--bg-surface-3-rgb) / <alpha-value>)',
			},
  			chart: {
				'1': 'rgb(var(--accent-rgb) / <alpha-value>)',
				'2': 'rgb(var(--positive-rgb) / <alpha-value>)',
				'3': 'rgb(var(--border-strong-rgb) / <alpha-value>)',
				'4': 'rgb(var(--accent-hover-rgb) / <alpha-value>)',
				'5': 'rgb(var(--negative-rgb) / <alpha-value>)'
  			}
  		},
  		borderRadius: {
			lg: 'var(--radius-lg)',
			md: 'var(--radius-md)',
			sm: 'var(--radius-sm)',
			xl: 'var(--radius-xl)',
			full: 'var(--radius-pill)'
  		},
  		keyframes: {
  			'accordion-down': {
  				from: {
  					height: '0'
  				},
  				to: {
  					height: 'var(--radix-accordion-content-height)'
  				}
  			},
  			'accordion-up': {
  				from: {
  					height: 'var(--radix-accordion-content-height)'
  				},
  				to: {
  					height: '0'
  				}
  			},
  			'scan': {
  				'0%': { transform: 'translateY(0)' },
  				'100%': { transform: 'translateY(4px)' }
  			},
  			'blink': {
  				'0%, 50%': { opacity: '1' },
  				'51%, 100%': { opacity: '0' }
  			},
  			'flicker': {
  				'0%, 100%': { opacity: '1' },
  				'50%': { opacity: '0.95' }
  			}
  		},
  		animation: {
  			'accordion-down': 'accordion-down 0.2s ease-out',
  			'accordion-up': 'accordion-up 0.2s ease-out',
  			'scan': 'scan 8s linear infinite',
  			'blink': 'blink 1s step-end infinite',
  			'flicker': 'flicker 0.15s ease-in-out infinite'
  		}
  	}
  },
  plugins: [require("tailwindcss-animate")],
} satisfies Config

export default config
