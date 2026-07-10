import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { resolve } from 'path'

// https://vite.dev/config/
// Architecture Reference: docs/frontend.md L3856-3871
// - Path alias: @/ → src/
// - Production: no source maps, strip console/debugger
// - Dev server: port 5173 (Vite default)
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
    },
  },
  server: {
    port: 5173,
  },
  build: {
    sourcemap: false,
    // Strip console.log and debugger statements in production builds
    // Architecture Reference: docs/implementation-roadmap.md L1671-1677
  },
  // Vite 8 uses OXC for transforms (replaces esbuild)
  oxc: {
    transform: {
      drop: ['console', 'debugger'],
    },
  },
})
