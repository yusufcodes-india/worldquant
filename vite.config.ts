// vite.config.ts
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { resolve } from 'path';

export default defineConfig({
  plugins: [react()],
  root: '.',
  build: {
    outDir: 'dist',
    rollupOptions: {
      input: {
        popup: resolve(__dirname, 'src/ui/popup/index.html'),
        dashboard: resolve(__dirname, 'src/ui/dashboard/index.html'),
        options: resolve(__dirname, 'src/ui/options/index.html'),
      },
    },
  },
  server: {
    port: 5173,
    strictPort: true,
  },
});
