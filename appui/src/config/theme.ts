import type { ThemeConfig } from 'antd/es/config-provider';

export type ThemeMode = 'light' | 'dark';

export const SKYLINE_LIGHT_TOKENS = {
  surface: '#f5f6ff',
  surfaceDim: '#c4d4fb',
  surfaceBright: '#f5f6ff',
  surfaceContainerLowest: '#ffffff',
  surfaceContainerLow: '#edf0ff',
  surfaceContainer: '#e0e8ff',
  surfaceContainerHigh: '#d8e2ff',
  surfaceContainerHighest: '#cfddff',
  onSurface: '#252f43',
  onSurfaceVariant: '#525b72',
  inverseSurface: '#040e21',
  inverseOnSurface: '#939db6',
  outline: '#6d778e',
  outlineVariant: '#a3adc7',
  surfaceTint: '#006382',
  primary: '#006382',
  onPrimary: '#e5f5ff',
  primaryContainer: '#7bd1fa',
  primaryAction: '#7dd3fc',
  onPrimaryContainer: '#00465d',
  secondary: '#346176',
  secondaryContainer: '#b1ddf7',
  tertiary: '#6f4b94',
  tertiaryContainer: '#d6adff',
  error: '#b31b25',
  success: '#07824f',
  chartUp: '#16b878',
  chartDown: '#ef4444',
} as const;

export const SKYLINE_DARK_TOKENS = {
  surface: '#081326',
  surfaceDim: '#081326',
  surfaceBright: '#2f394e',
  surfaceContainerLowest: '#040e21',
  surfaceContainerLow: '#111b2f',
  surfaceContainer: '#151f33',
  surfaceContainerHigh: '#202a3e',
  surfaceContainerHighest: '#2b354a',
  onSurface: '#d8e2fd',
  onSurfaceVariant: '#bec8ce',
  inverseSurface: '#d8e2fd',
  inverseOnSurface: '#263045',
  outline: '#899298',
  outlineVariant: '#3f484e',
  surfaceTint: '#7bd1fa',
  primary: '#c5eaff',
  onPrimary: '#003547',
  primaryContainer: '#7dd3fc',
  primaryAction: '#7dd3fc',
  onPrimaryContainer: '#005b78',
  secondary: '#a0cde5',
  secondaryContainer: '#1f4e63',
  tertiary: '#f1ddff',
  tertiaryContainer: '#ddbaff',
  error: '#ffb4ab',
  success: '#7dd9ac',
  chartUp: '#16b878',
  chartDown: '#fb5151',
} as const;

export const SKYLINE_TOKENS = SKYLINE_LIGHT_TOKENS;

export function getSkylineTokens(themeMode: ThemeMode) {
  return themeMode === 'dark' ? SKYLINE_DARK_TOKENS : SKYLINE_LIGHT_TOKENS;
}

export const CHART_PALETTE = {
  china: {
    up: SKYLINE_LIGHT_TOKENS.chartUp,
    down: SKYLINE_LIGHT_TOKENS.chartDown,
    upVolume: 'rgba(22, 184, 120, 0.28)',
    downVolume: 'rgba(239, 68, 68, 0.28)',
  },
  international: {
    up: SKYLINE_LIGHT_TOKENS.chartUp,
    down: SKYLINE_LIGHT_TOKENS.chartDown,
    upVolume: 'rgba(22, 184, 120, 0.28)',
    downVolume: 'rgba(239, 68, 68, 0.28)',
  },
} as const;

export const CHART_THEME = {
  light: {
    background: SKYLINE_LIGHT_TOKENS.surfaceContainerLowest,
    text: SKYLINE_LIGHT_TOKENS.onSurfaceVariant,
    grid: '#e8edfb',
    crosshair: '#8fa2bd',
    border: '#dbe3f4',
    labelBackground: SKYLINE_LIGHT_TOKENS.primary,
    priceLine: SKYLINE_LIGHT_TOKENS.primary,
  },
  dark: {
    background: SKYLINE_DARK_TOKENS.surfaceContainerLowest,
    text: SKYLINE_DARK_TOKENS.onSurfaceVariant,
    grid: '#202a3e',
    crosshair: '#899298',
    border: SKYLINE_DARK_TOKENS.outlineVariant,
    labelBackground: SKYLINE_DARK_TOKENS.primaryContainer,
    priceLine: SKYLINE_DARK_TOKENS.primaryContainer,
  },
} as const;

export function getAntTheme(themeMode: ThemeMode): ThemeConfig {
  const tokens = getSkylineTokens(themeMode);
  const isDark = themeMode === 'dark';

  return {
    token: {
    borderRadius: 8,
    borderRadiusLG: 16,
    borderRadiusSM: 8,
    boxShadow: isDark ? '0 18px 48px rgba(0, 0, 0, 0.28)' : '0 18px 48px rgba(26, 36, 56, 0.08)',
    boxShadowSecondary: isDark ? '0 10px 28px rgba(0, 0, 0, 0.24)' : '0 10px 28px rgba(26, 36, 56, 0.07)',
    colorBgBase: tokens.surface,
    colorBgContainer: tokens.surfaceContainerLowest,
    colorBgElevated: tokens.surfaceContainerLow,
    colorBgLayout: tokens.surface,
    colorBorder: tokens.outlineVariant,
    colorBorderSecondary: isDark ? '#2b354a' : '#d7def1',
    colorError: tokens.error,
    colorFill: isDark ? 'rgba(123, 209, 250, 0.1)' : 'rgba(0, 99, 130, 0.08)',
    colorFillSecondary: isDark ? 'rgba(221, 186, 255, 0.13)' : 'rgba(123, 209, 250, 0.18)',
    colorInfo: tokens.primary,
    colorLink: tokens.primary,
    colorPrimary: tokens.primary,
    colorPrimaryBg: isDark ? '#1f4e63' : '#dcf4ff',
    colorPrimaryBgHover: isDark ? '#2b627a' : '#c8ecff',
    colorPrimaryBorder: tokens.primaryContainer,
    colorPrimaryHover: tokens.primaryContainer,
    colorSuccess: tokens.success,
    colorSplit: isDark ? '#2b354a' : '#dbe3f4',
    colorText: tokens.onSurface,
    colorTextHeading: tokens.onSurface,
    colorTextSecondary: tokens.onSurfaceVariant,
    fontFamily: 'Inter, ui-sans-serif, system-ui, sans-serif',
    fontSize: 14,
    fontSizeHeading3: 24,
    fontSizeHeading4: 18,
    lineHeight: 1.5,
    controlHeight: 36,
    controlHeightLG: 44,
    wireframe: false,
  },
  components: {
    Button: {
      borderRadius: 8,
      colorPrimary: tokens.primaryContainer,
      colorPrimaryActive: isDark ? '#7bd1fa' : '#6cc3eb',
      colorPrimaryHover: tokens.primaryAction,
      primaryColor: isDark ? '#003547' : '#003041',
      primaryShadow: isDark ? '0 10px 24px rgba(123, 209, 250, 0.16)' : '0 10px 24px rgba(0, 99, 130, 0.16)',
    },
    Card: {
      borderRadiusLG: 16,
      colorBgContainer: tokens.surfaceContainerLowest,
      boxShadowTertiary: isDark ? '0 18px 48px rgba(0, 0, 0, 0.28)' : '0 18px 48px rgba(26, 36, 56, 0.08)',
    },
    Layout: {
      bodyBg: tokens.surface,
      headerBg: tokens.surfaceContainerLowest,
      siderBg: tokens.surfaceContainerLowest,
    },
    Menu: {
      itemBg: 'transparent',
      itemColor: tokens.onSurfaceVariant,
      itemHoverColor: tokens.primary,
      itemSelectedBg: tokens.surfaceContainerHigh,
      itemSelectedColor: tokens.primary,
    },
    Table: {
      borderColor: isDark ? '#2b354a' : '#d7def1',
      colorBgContainer: tokens.surfaceContainerLowest,
      headerBg: tokens.surfaceContainerLow,
    },
    Segmented: {
      itemActiveBg: tokens.surfaceContainerLowest,
      itemSelectedBg: tokens.primaryContainer,
      itemSelectedColor: tokens.onPrimaryContainer,
      trackBg: tokens.surfaceContainerLow,
    },
  },
};
}

export const ANT_THEME: ThemeConfig = getAntTheme('light');
