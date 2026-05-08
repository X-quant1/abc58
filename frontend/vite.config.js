import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    host: '127.0.0.1',  // 强制使用 IPv4
    watch: {
      usePolling: false,
      ignored: ['**/node_modules/**', '**/dist/**', '**/.git/**'],
    },
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',  // 使用 IPv4 地址
        changeOrigin: true,
      },
      '/ws': {
        target: 'ws://127.0.0.1:8000',
        ws: true,
        changeOrigin: true,
      },
      '/static': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})
