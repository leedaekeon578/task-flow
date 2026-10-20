import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// 화면은 /api 로 요청하고, 개발 서버가 FastAPI(8000)로 넘긴다.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
      },
    },
  },
})
