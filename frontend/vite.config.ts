import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { defineConfig, type PluginOption } from 'vite'
import cesiumImport from 'vite-plugin-cesium'

// vite-plugin-cesium ships ESM-style .d.ts in a CJS package; runtime resolves the .mjs default fine.
const cesium = cesiumImport as unknown as () => PluginOption

export default defineConfig({
  plugins: [react(), tailwindcss(), cesium()],
  server: { port: 5173 },
})
