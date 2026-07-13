import { MAX_WINDOW, PRELOAD_BARS } from '../config/chart';

export interface LogicalRangeLike {
  from: number;
  to: number;
}

export interface KLineRangePreloadInput {
  offset: number;
  total: number;
  candlesLength: number;
  range: LogicalRangeLike | null;
}

export interface KLineRangePreloadRequest {
  left: number;
  right: number;
}

type PanDirection = 'left' | 'right';

function clamp(value: number, min: number, max: number) {
  return Math.min(Math.max(value, min), max);
}

function choosePanDirection(
  needLeft: boolean,
  needRight: boolean,
  leftDistance: number,
  rightDistance: number,
): PanDirection {
  if (needLeft && needRight) {
    return leftDistance <= rightDistance ? 'left' : 'right';
  }

  return needLeft ? 'left' : 'right';
}

export function createKLineRangePreloadPlanner() {
  let lastEmittedRangeKey = '';

  return {
    reset() {
      lastEmittedRangeKey = '';
    },

    next({
      candlesLength: loadedLength,
      offset: loadedOffset,
      range,
      total: currentTotal,
    }: KLineRangePreloadInput): KLineRangePreloadRequest | null {
      if (!range || !loadedLength || !currentTotal) return null;

      const localLeft = Math.floor(range.from);
      const localRight = Math.ceil(range.to);
      const globalLeft = loadedOffset + localLeft;
      const globalRight = loadedOffset + localRight;
      const loadedRight = loadedOffset + loadedLength - 1;

      if (globalRight < 0 && loadedOffset === 0) return null;
      if (globalLeft >= currentTotal && loadedRight >= currentTotal - 1) return null;

      const visibleLeft = clamp(globalLeft, 0, currentTotal - 1);
      const visibleRight = clamp(globalRight, 0, currentTotal - 1);
      const leftDistance = visibleLeft - loadedOffset;
      const rightDistance = loadedRight - visibleRight;
      const needLeft = leftDistance <= PRELOAD_BARS / 2 && loadedOffset > 0;
      const needRight =
        rightDistance <= PRELOAD_BARS / 2 && loadedRight < currentTotal - 1;

      if (!needLeft && !needRight) return null;

      const direction = choosePanDirection(
        needLeft,
        needRight,
        leftDistance,
        rightDistance,
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

      if (targetLeft === loadedOffset && targetRight === loadedRight) return null;

      const combinedKey = `${targetLeft}:${targetRight}`;
      if (combinedKey === lastEmittedRangeKey) return null;
      lastEmittedRangeKey = combinedKey;

      return {
        left: targetLeft,
        right: targetRight,
      };
    },
  };
}
