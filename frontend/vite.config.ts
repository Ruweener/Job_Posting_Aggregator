import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // During development the React app runs on :5173 and FastAPI on :8000. The browser only
    // talks to :5173. Vite forwards anything under /api to FastAPI with the /api prefix removed,
    // so /api/postings goes to http://127.0.0.1:8000/postings. Same origin = no CORS setup.
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
})
