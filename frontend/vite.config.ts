import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import { fileURLToPath } from 'node:url';

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  const origin = loadEnv(mode, process.cwd()).VITE_API_ORIGIN;
  if (origin) {
    const url = new URL(origin);
    const local = mode === 'development' && url.protocol === 'http:' && ['localhost', '127.0.0.1', '[::1]'].includes(url.hostname);
    if ((url.protocol !== 'https:' && !local) || url.username || url.password || url.search || url.hash || url.pathname !== '/') {
      throw new Error('VITE_API_ORIGIN must be an HTTPS origin; loopback HTTP is allowed in development.');
    }
  }
  return {
  plugins: [react()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    port: 3000,
    strictPort: true,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
  preview: {
    port: 4173
  }
  };
});
