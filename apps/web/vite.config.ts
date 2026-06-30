/// <reference types="vitest/config" />
import react from '@vitejs/plugin-react';
import path from 'path';
import { defineConfig } from 'vite';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
    // In dev, proxy API calls through Vite so the browser never hits a different
    // origin and CORS is never a concern regardless of which port Vite picks.
    proxy: {
      '/ingest': { target: 'http://localhost:8001', changeOrigin: true },
      '/chat': { target: 'http://localhost:8002', changeOrigin: true },
      '/sessions': { target: 'http://localhost:8002', changeOrigin: true },
      '/analytics': { target: 'http://localhost:8003', changeOrigin: true },
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test-setup.ts'],
  },
});
