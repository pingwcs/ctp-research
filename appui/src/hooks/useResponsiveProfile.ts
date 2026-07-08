import { useEffect, useMemo, useState } from 'react';

import {
  getChartViewport,
  getResponsiveScale,
  readScreenSnapshot,
  type ScreenSnapshot,
} from '../config/responsive';

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

  return useMemo(
    () => ({
      ...snapshot,
      scale: getResponsiveScale(snapshot),
      chartViewport: getChartViewport(snapshot),
    }),
    [snapshot],
  );
}
