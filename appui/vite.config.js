import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
var appApiTarget = process.env.VITE_APPAPI_TARGET || 'http://127.0.0.1:8000';
export default defineConfig({
    plugins: [react()],
    resolve: {
        dedupe: ['react', 'react-dom'],
    },
    server: {
        port: 5173,
        proxy: {
            '/api': {
                target: appApiTarget,
                changeOrigin: true,
            },
        },
    },
});
