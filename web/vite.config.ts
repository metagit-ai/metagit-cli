import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  base: '/',
  build: {
    outDir: '../src/metagit/data/web',
    emptyOutDir: true,
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes('node_modules/three')) {
            return 'three-vendor'
          }
          if (id.includes('/components/terrain/terrainScene') || id.includes('/components/terrain/terrainTileMaterial')) {
            return 'terrain-scene'
          }
        },
      },
    },
  },
  server: {
    proxy: {
      '/v2': {
        target: 'http://127.0.0.1:8787',
        changeOrigin: true,
      },
      '/v3': {
        target: 'http://127.0.0.1:8787',
        changeOrigin: true,
      },
    },
  },
})
