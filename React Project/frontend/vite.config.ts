import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
import path from 'node:path';

const BACKEND = process.env.VITE_BACKEND_URL ?? 'http://127.0.0.1:8002';

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },

  server: {
    port: 5173,
    proxy: {
      // SHAP can take 20-30 min on CPU — set a long timeout so the proxy
      // doesn't drop the connection before the response arrives.
      '/api/scan/': {
        target: BACKEND,
        changeOrigin: true,
        timeout: 40 * 60 * 1000,        // 40 minutes
        proxyTimeout: 40 * 60 * 1000,   // 40 minutes
      },
      '/api': { target: BACKEND, changeOrigin: true, timeout: 60_000, proxyTimeout: 60_000 },
      '/health': { target: BACKEND, changeOrigin: true },
    },
  },
});
