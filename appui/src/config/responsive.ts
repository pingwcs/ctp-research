export type DeviceKind = 'pc' | 'android' | 'ios';

export const DESIGN_VIEWPORT = {
  width: 1920,
  height: 1080,
} as const;

export const ROOT_FONT_BASE = 100;

export interface ScreenSnapshot {
  deviceKind: DeviceKind;
  viewportWidth: number;
  viewportHeight: number;
  screenWidth: number;
  screenHeight: number;
  hardwareViewportWidth: number;
  hardwareViewportHeight: number;
  hardwareScreenWidth: number;
  hardwareScreenHeight: number;
  devicePixelRatio: number;
  isPortrait: boolean;
}

export interface ResponsiveScale {
  hardwareScale: number;
  fontScale: number;
  rootFontSize: number;
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

const SCALE_LIMITS = {
  min: 0.72,
  max: 1.6,
} as const;

export const DEFAULT_SCREEN_SNAPSHOT: ScreenSnapshot = {
  deviceKind: 'pc',
  viewportWidth: DESIGN_VIEWPORT.width,
  viewportHeight: DESIGN_VIEWPORT.height,
  screenWidth: DESIGN_VIEWPORT.width,
  screenHeight: DESIGN_VIEWPORT.height,
  hardwareViewportWidth: DESIGN_VIEWPORT.width,
  hardwareViewportHeight: DESIGN_VIEWPORT.height,
  hardwareScreenWidth: DESIGN_VIEWPORT.width,
  hardwareScreenHeight: DESIGN_VIEWPORT.height,
  devicePixelRatio: 1,
  isPortrait: false,
};

function clamp(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value));
}

function roundPixel(value: number) {
  return Math.round(value * 100) / 100;
}

function getDevicePixelRatio(windowRef: Window) {
  const ratio = windowRef.devicePixelRatio || 1;
  return Number.isFinite(ratio) && ratio > 0 ? ratio : 1;
}

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

export function readScreenSnapshot(): ScreenSnapshot {
  if (typeof window === 'undefined') {
    return DEFAULT_SCREEN_SNAPSHOT;
  }

  const viewportWidth = window.visualViewport?.width ?? window.innerWidth;
  const viewportHeight = window.visualViewport?.height ?? window.innerHeight;
  const screenWidth = window.screen.width;
  const screenHeight = window.screen.height;
  const devicePixelRatio = getDevicePixelRatio(window);

  return {
    deviceKind: detectDeviceKind(
      window.navigator.userAgent,
      window.navigator.platform,
      window.navigator.maxTouchPoints,
    ),
    viewportWidth,
    viewportHeight,
    screenWidth,
    screenHeight,
    hardwareViewportWidth: viewportWidth * devicePixelRatio,
    hardwareViewportHeight: viewportHeight * devicePixelRatio,
    hardwareScreenWidth: screenWidth * devicePixelRatio,
    hardwareScreenHeight: screenHeight * devicePixelRatio,
    devicePixelRatio,
    isPortrait: viewportHeight >= viewportWidth,
  };
}

export function getResponsiveScale(snapshot: ScreenSnapshot): ResponsiveScale {
  const widthScale = snapshot.hardwareViewportWidth / DESIGN_VIEWPORT.width;
  const heightScale = snapshot.hardwareViewportHeight / DESIGN_VIEWPORT.height;
  const hardwareScale = Math.min(widthScale, heightScale);
  const fontScale = clamp(hardwareScale, SCALE_LIMITS.min, SCALE_LIMITS.max);

  return {
    hardwareScale: roundPixel(hardwareScale),
    fontScale: roundPixel(fontScale),
    rootFontSize: roundPixel(ROOT_FONT_BASE * fontScale),
  };
}

export function applyRootFontSize(snapshot = readScreenSnapshot()) {
  if (typeof document === 'undefined') return;

  // CSS is authored from the 1920x1080 design in rem units; the runtime
  // root font size maps those design pixels onto the current hardware pixels.
  document.documentElement.style.fontSize = `${getResponsiveScale(snapshot).rootFontSize}px`;
}

export function installResponsiveRootFont() {
  if (typeof window === 'undefined') {
    return () => undefined;
  }

  const update = () => applyRootFontSize();
  update();

  window.addEventListener('resize', update);
  window.addEventListener('orientationchange', update);
  window.visualViewport?.addEventListener('resize', update);

  return () => {
    window.removeEventListener('resize', update);
    window.removeEventListener('orientationchange', update);
    window.visualViewport?.removeEventListener('resize', update);
  };
}

export function getChartViewport(snapshot: ScreenSnapshot): ChartViewportConfig {
  const rule = CHART_SIZE_RULES[snapshot.deviceKind];
  const { fontScale } = getResponsiveScale(snapshot);
  const availableHeight = snapshot.viewportHeight - rule.chromeOffset * fontScale;

  return {
    height: Math.round(Math.max(rule.minHeight * fontScale, availableHeight)),
    maxWidth: '100%',
    maxHeight: '100%',
  };
}
