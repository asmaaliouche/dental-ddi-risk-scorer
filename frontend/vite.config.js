import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      // Proxy API calls to the FastAPI backend during development
      '/check': 'http://localhost:8000',
      '/dental-drugs': 'http://localhost:8000',
      '/patient-drugs': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
    }
  }
})
