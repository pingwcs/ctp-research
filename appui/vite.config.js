import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { visualizer } from 'rollup-plugin-visualizer';
var appApiTarget = process.env.VITE_APPAPI_TARGET || 'http://127.0.0.1:8000';
var shouldAnalyzeBundle = process.env.ANALYZE === 'true';
function normalizeModuleId(id) {
    return id.replace(/\\/g, '/');
}
function getManualChunk(id) {
    var moduleId = normalizeModuleId(id);
    if (moduleId.includes('/src/pages/KLinePage') ||
        moduleId.includes('/src/pages/kline/') ||
        moduleId.includes('/src/components/KLineChart') ||
        moduleId.includes('/src/components/kline/')) {
        return 'kline-page';
    }
    if (moduleId.includes('/src/pages/backtest/') ||
        moduleId.includes('/src/components/EquityChart')) {
        return 'backtest-results';
    }
    if (moduleId.includes('/src/pages/BacktestPage'))
        return 'backtest-page';
    if (moduleId.includes('/src/pages/HomePage'))
        return 'home-page';
    if (!moduleId.includes('/node_modules/'))
        return undefined;
    if (moduleId.includes('/node_modules/react/') ||
        moduleId.includes('/node_modules/react-dom/') ||
        moduleId.includes('/node_modules/react-router') ||
        moduleId.includes('/node_modules/scheduler/')) {
        return 'react-vendor';
    }
    if (moduleId.includes('/node_modules/antd/es/config-provider/') ||
        moduleId.includes('/node_modules/antd/es/empty/') ||
        moduleId.includes('/node_modules/antd/es/layout/') ||
        moduleId.includes('/node_modules/antd/es/menu/') ||
        moduleId.includes('/node_modules/antd/es/theme/') ||
        moduleId.includes('/node_modules/antd/es/typography/') ||
        moduleId.includes('/node_modules/@ant-design/colors/') ||
        moduleId.includes('/node_modules/@ant-design/cssinjs/') ||
        moduleId.includes('/node_modules/rc-menu/') ||
        moduleId.includes('/node_modules/rc-overflow/')) {
        return 'antd-vendor';
    }
    if (moduleId.includes('/node_modules/lightweight-charts/'))
        return 'chart-vendor';
    if (moduleId.includes('/node_modules/@reduxjs/toolkit/') ||
        moduleId.includes('/node_modules/react-redux/') ||
        moduleId.includes('/node_modules/redux/') ||
        moduleId.includes('/node_modules/reselect/') ||
        moduleId.includes('/node_modules/immer/')) {
        return 'state-vendor';
    }
    return undefined;
}
export default defineConfig({
    plugins: [
        react(),
        shouldAnalyzeBundle &&
            visualizer({
                brotliSize: true,
                filename: 'dist/bundle-stats.html',
                gzipSize: true,
                template: 'treemap',
            }),
    ],
    resolve: {
        dedupe: ['react', 'react-dom'],
    },
    build: {
        rollupOptions: {
            output: {
                manualChunks: getManualChunk,
            },
        },
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
