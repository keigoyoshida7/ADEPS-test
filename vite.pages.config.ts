import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/postcss';
export default defineConfig(({ command, isPreview }) => ({
  base:
    command === 'serve' && !isPreview ? '/' : process.env.VITE_BASE_PATH || '/ADEPS-test/',
  plugins: [react()],
  css: { postcss: { plugins: [tailwindcss()] } },
  server: {
    host: '127.0.0.1',
    port: 5178,
    strictPort: true,
    proxy: {
      '/lab-api': {
        target: 'http://127.0.0.1:8871',
        rewrite: (path) => path.replace(/^\/lab-api/, '/api'),
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
    rollupOptions: { input: 'index.html' },
  },
}));
