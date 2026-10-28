// vite.config.ts
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import * as path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

export default defineConfig({
  plugins: [react()],
  root: '.',
  build: {
    outDir: 'dist',
    rollupOptions: {
      input: {
        popup: path.resolve(__dirname, 'src/ui/popup/index.html'),
        dashboard: path.resolve(__dirname, 'src/ui/dashboard/index.html'),
        options: path.resolve(__dirname, 'src/ui/options/index.html'),
        background: path.resolve(__dirname, 'src/background/index.ts'),
      },
    },
  },
  server: {
    port: 5180,
  },
});