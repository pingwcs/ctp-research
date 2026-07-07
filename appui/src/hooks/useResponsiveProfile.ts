import { useEffect, useState } from 'react';

import {
  DEFAULT_SCREEN_SNAPSHOT,
  detectDeviceKind,
  getChartViewport,
  type ScreenSnapshot,
} from '../config/responsive';

function readScreenSnapshot(): ScreenSnapshot {
  if (typeof window === 'undefined') {
    return DEFAULT_SCREEN_SNAPSHOT;
  }

  const viewportWidth = window.visualViewport?.width ?? window.innerWidth;
  const viewportHeight = window.visualViewport?.height ?? window.innerHeight;
  const deviceKind = detectDeviceKind(
    window.navigator.userAgent,
    window.navigator.platform,
    window.navigator.maxTouchPoints,
  );

  return {
    deviceKind,
    viewportWidth,
    viewportHeight,
    screenWidth: window.screen.width,
    screenHeight: window.screen.height,
    devicePixelRatio: window.devicePixelRatio || 1,
    isPortrait: viewportHeight >= viewportWidth,
  };
}

export function useResponsiveProfile() {
  const [snapshot, setSnapshot] = useState<ScreenSnapshot>(() => readScreenSnapshot());

  useEffect(() => {
    const update = () => setSnapshot(readScreenSnapshot());

    window.addEventListener('resize', update);
    window.addEventListener('orientationchange', update);
    window.visualViewport?.addEventListener('resize', update);

    return () => {
      window.removeEventListener('resize', update);
      window.removeEventListener('orientationchange', update);
      window.visualViewport?.removeEventListener('resize', update);
    };
  }, []);

  return {
    ...snapshot,
    chartViewport: getChartViewport(snapshot),
  };
}
