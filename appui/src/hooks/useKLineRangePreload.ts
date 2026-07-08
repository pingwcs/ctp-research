import { useCallback, useEffect, useRef, type MutableRefObject } from 'react';

import { MAX_WINDOW, PRELOAD_BARS } from '../config/chart';

export interface LogicalRangeLike {
  from: number;
  to: number;
}

type PanDirection = 'left' | 'right';

interface VisibleWindowSnapshot {
  center: number;
  left: number;
  right: number;
}

interface UseKLineRangePreloadParams {
  offset: number;
  total: number;
  candlesLength: number;
  onRequestRange?: (left: number, right: number) => void;
  resetKey?: string;
  suppressRef?: MutableRefObject<boolean>;
}

function clamp(value: number, min: number, max: number) {
  return Math.min(Math.max(value, min), max);
}

function choosePanDirection(
  needLeft: boolean,
  needRight: boolean,
  leftDistance: number,
  rightDistance: number,
  previousWindow: VisibleWindowSnapshot | null,
  visibleCenter: number,
): PanDirection {
  if (needLeft && needRight) {
    if (previousWindow) {
      if (visibleCenter < previousWindow.center) return 'left';
      if (visibleCenter > previousWindow.center) return 'right';
    }

    return leftDistance <= rightDistance ? 'left' : 'right';
  }

  return needLeft ? 'left' : 'right';
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
  const lastVisibleWindowRef = useRef<VisibleWindowSnapshot | null>(null);

  latestRef.current = {
    candlesLength,
    offset,
    onRequestRange,
    total,
  };

  useEffect(() => {
    lastEmittedRangeKeyRef.current = '';
    lastVisibleWindowRef.current = null;
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

      if (globalRight < 0 || globalLeft >= currentTotal) return;

      const visibleLeft = clamp(globalLeft, 0, currentTotal - 1);
      const visibleRight = clamp(globalRight, 0, currentTotal - 1);
      const loadedRight = loadedOffset + loadedLength - 1;
      const leftDistance = visibleLeft - loadedOffset;
      const rightDistance = loadedRight - visibleRight;
      const needLeft = leftDistance <= PRELOAD_BARS / 2 && loadedOffset > 0;
      const needRight =
        rightDistance <= PRELOAD_BARS / 2 && loadedRight < currentTotal - 1;

      const visibleCenter = (visibleLeft + visibleRight) / 2;
      const previousVisibleWindow = lastVisibleWindowRef.current;
      lastVisibleWindowRef.current = {
        center: visibleCenter,
        left: visibleLeft,
        right: visibleRight,
      };

      if (!needLeft && !needRight) return;

      const direction = choosePanDirection(
        needLeft,
        needRight,
        leftDistance,
        rightDistance,
        previousVisibleWindow,
        visibleCenter,
      );
      const windowSize = Math.min(MAX_WINDOW, currentTotal);
      const maxOffset = Math.max(0, currentTotal - windowSize);
      const requestStep = Math.max(1, Math.min(PRELOAD_BARS, windowSize));
      let targetLeft =
        loadedOffset + (direction === 'left' ? -requestStep : requestStep);

      if (direction === 'left') {
        targetLeft = Math.min(targetLeft, visibleLeft);
      } else {
        targetLeft = Math.max(targetLeft, visibleRight - windowSize + 1);
      }

      targetLeft = clamp(Math.round(targetLeft), 0, maxOffset);
      const targetRight = Math.min(currentTotal - 1, targetLeft + windowSize - 1);

      if (targetLeft === loadedOffset && targetRight === loadedRight) return;

      const combinedKey = `${targetLeft}:${targetRight}`;
      if (combinedKey === lastEmittedRangeKeyRef.current) return;
      lastEmittedRangeKeyRef.current = combinedKey;

      requestRange(targetLeft, targetRight);
    },
    [suppressRef],
  );
}
