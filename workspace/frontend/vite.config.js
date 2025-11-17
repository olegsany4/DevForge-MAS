import { defineConfig } from 'vite';
export default defineConfig({
    server: {
        port: 5173,
        proxy: {
            // Проксируем ТОЛЬКО API; контракты отдаём статикой из /public
            '/api': { target: 'http://localhost:8000', changeOrigin: true }
        }
    }
});
