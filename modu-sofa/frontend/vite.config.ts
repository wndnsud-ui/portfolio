import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  // 루트(modu-sofa/.env)의 VITE_ 변수를 읽는다
  envDir: '..',
  server: { port: 5173 },
});
