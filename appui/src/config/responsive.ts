export type DeviceKind = 'pc' | 'android' | 'ios';

export interface ScreenSnapshot {
  deviceKind: DeviceKind;
  viewportWidth: number;
  viewportHeight: number;
  screenWidth: number;
  screenHeight: number;
  devicePixelRatio: number;
  isPortrait: boolean;
}

export interface ChartViewportConfig {
  height: number;
  maxWidth: string;
  maxHeight: string;
}

const CHART_SIZE_RULES: Record<DeviceKind, { minHeight: number; chromeOffset: number }> = {
  pc: {
    minHeight: 520,
    chromeOffset: 300,
  },
  android: {
    minHeight: 360,
    chromeOffset: 340,
  },
  ios: {
    minHeight: 360,
    chromeOffset: 360,
  },
};

export const DEFAULT_SCREEN_SNAPSHOT: ScreenSnapshot = {
  deviceKind: 'pc',
  viewportWidth: 1440,
  viewportHeight: 900,
  screenWidth: 1440,
  screenHeight: 900,
  devicePixelRatio: 1,
  isPortrait: false,
};

export function detectDeviceKind(
  userAgent: string,
  platform = '',
  maxTouchPoints = 0,
): DeviceKind {
  const normalizedAgent = userAgent.toLowerCase();
  const normalizedPlatform = platform.toLowerCase();

  if (/android/.test(normalizedAgent)) {
    return 'android';
  }

  const isAppleMobile = /iphone|ipad|ipod/.test(normalizedAgent);
  const isTouchMac = normalizedPlatform.includes('mac') && maxTouchPoints > 1;
  if (isAppleMobile || isTouchMac) {
    return 'ios';
  }

  return 'pc';
}

export function getChartViewport(snapshot: ScreenSnapshot): ChartViewportConfig {
  const rule = CHART_SIZE_RULES[snapshot.deviceKind];
  const availableHeight = snapshot.viewportHeight - rule.chromeOffset;
  return {
    height: Math.max(rule.minHeight, availableHeight),
    maxWidth: '100%',
    maxHeight: '100%',
  };
}
