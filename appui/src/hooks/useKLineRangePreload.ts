import { useCallback, useEffect, useRef, type MutableRefObject } from 'react';

import { MAX_WINDOW, PRELOAD_BARS } from '../config/chart';

export interface LogicalRangeLike {
  from: number;
  to: number;
}

interface UseKLineRangePreloadParams {
  offset: number;
  total: number;
  candlesLength: number;
  onRequestRange?: (left: number, right: number) => void;
  resetKey?: string;
  suppressRef?: MutableRefObject<boolean>;
}

export function useKLineRangePreload({
  offset,
  total,
  candlesLength,
  onRequestRange,
  resetKey,
  suppressRef,
}: UseKLineRangePreloadParams) {
  const latestRef = useRef({
    candlesLength,
    offset,
    onRequestRange,
    total,
  });
  const lastEmittedRangeKeyRef = useRef('');

  latestRef.current = {
    candlesLength,
    offset,
    onRequestRange,
    total,
  };

  useEffect(() => {
    lastEmittedRangeKeyRef.current = '';
  }, [resetKey, total]);

  return useCallback(
    (range: LogicalRangeLike | null) => {
      if (!range) return;
      if (suppressRef?.current) return;

      const {
        candlesLength: loadedLength,
        offset: loadedOffset,
        onRequestRange: requestRange,
        total: currentTotal,
      } = latestRef.current;

      if (!requestRange || !loadedLength || !currentTotal) return;

      const localLeft = Math.floor(range.from);
      const localRight = Math.ceil(range.to);
      const globalLeft = loadedOffset + localLeft;
      const globalRight = loadedOffset + localRight;

      if (globalLeft < 0 || globalRight >= currentTotal) return;

      const loadedRight = loadedOffset + loadedLength - 1;
      const needLeft = globalLeft - loadedOffset <= PRELOAD_BARS / 2 && loadedOffset > 0;
      const needRight =
        loadedRight - globalRight <= PRELOAD_BARS / 2 && loadedRight < currentTotal - 1;

      if (!needLeft && !needRight) return;

      let targetLeft = Math.max(0, globalLeft - PRELOAD_BARS);
      let targetRight = Math.min(currentTotal - 1, globalRight + PRELOAD_BARS);

      if (targetRight - targetLeft + 1 > MAX_WINDOW) {
        const center = Math.floor((globalLeft + globalRight) / 2);
        targetLeft = Math.max(0, center - Math.floor(MAX_WINDOW / 2));
        targetRight = Math.min(currentTotal - 1, targetLeft + MAX_WINDOW - 1);
      }

      const combinedKey = `${targetLeft}:${targetRight}`;
      if (combinedKey === lastEmittedRangeKeyRef.current) return;
      lastEmittedRangeKeyRef.current = combinedKey;

      requestRange(targetLeft, targetRight);
    },
    [suppressRef],
  );
}
