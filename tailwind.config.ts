import type { Config } from 'tailwindcss'
import daisyui from 'daisyui'

export default {
  content: ['./index.html', './app/**/*.{vue,js,ts,jsx,tsx}'],
  plugins: [daisyui],
  daisyui: {
    themes: ['light', 'dark']
  }
} satisfies Config
