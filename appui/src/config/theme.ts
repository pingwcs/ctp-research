import type { ThemeConfig } from 'antd';

export const CHART_PALETTE = {
  china: {
    up: '#ef4444',
    down: '#22c55e',
    upVolume: 'rgba(239, 68, 68, 0.35)',
    downVolume: 'rgba(34, 197, 94, 0.35)',
  },
  international: {
    up: '#22c55e',
    down: '#ef4444',
    upVolume: 'rgba(34, 197, 94, 0.35)',
    downVolume: 'rgba(239, 68, 68, 0.35)',
  },
} as const;

export const ANT_THEME: ThemeConfig = {
  token: {
    borderRadius: 6,
    colorBgBase: '#09090b',
    colorBgContainer: '#111113',
    colorBorder: '#27272a',
    colorPrimary: '#0891b2',
    colorText: '#f4f4f5',
    colorTextSecondary: '#a1a1aa',
    fontFamily: 'Inter, ui-sans-serif, system-ui, sans-serif',
  },
  components: {
    Card: {
      colorBgContainer: '#111113',
    },
    Layout: {
      bodyBg: '#09090b',
      headerBg: '#09090b',
      siderBg: '#09090b',
    },
  },
};
