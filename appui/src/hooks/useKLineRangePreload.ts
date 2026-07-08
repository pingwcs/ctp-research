import { useCallback, useEffect, useRef, type MutableRefObject } from 'react';

import { MAX_WINDOW, PRELOAD_BARS } from '../config/chart';

export interface LogicalRangeLike {
  from: number;
  to: number;
}

type PanDirection = 'left' | 'right';

interface VisibleWindowSnapshot {
  center: number;
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
  userPanDirection: PanDirection,
): PanDirection {
  if (needLeft && needRight) {
    return userPanDirection;
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
      const loadedRight = loadedOffset + loadedLength - 1;

      if (globalRight < 0 && loadedOffset === 0) return;
      if (globalLeft >= currentTotal && loadedRight >= currentTotal - 1) return;

      const visibleLeft = clamp(globalLeft, 0, currentTotal - 1);
      const visibleRight = clamp(globalRight, 0, currentTotal - 1);
      const leftDistance = visibleLeft - loadedOffset;
      const rightDistance = loadedRight - visibleRight;
      const needLeft = leftDistance <= PRELOAD_BARS / 2 && loadedOffset > 0;
      const needRight =
        rightDistance <= PRELOAD_BARS / 2 && loadedRight < currentTotal - 1;

      const visibleCenter = (visibleLeft + visibleRight) / 2;
      const previousVisibleWindow = lastVisibleWindowRef.current;
      lastVisibleWindowRef.current = {
        center: visibleCenter,
      };

      if (!needLeft && !needRight) return;

      if (!previousVisibleWindow) return;

      let userPanDirection: PanDirection | null = null;
      if (visibleCenter < previousVisibleWindow.center - 1) {
        userPanDirection = 'left';
      } else if (visibleCenter > previousVisibleWindow.center + 1) {
        userPanDirection = 'right';
      }

      if (!userPanDirection) return;
      if (needLeft && !needRight && userPanDirection !== 'left') return;
      if (needRight && !needLeft && userPanDirection !== 'right') return;

      const direction = choosePanDirection(
        needLeft,
        needRight,
        userPanDirection,
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
