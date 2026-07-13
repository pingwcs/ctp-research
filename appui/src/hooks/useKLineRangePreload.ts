import { useCallback, useEffect, useRef, type MutableRefObject } from 'react';

import { createKLineRangePreloadPlanner } from './klineRangePreloadPlanner';
import type { LogicalRangeLike } from './klineRangePreloadPlanner';

export type { LogicalRangeLike } from './klineRangePreloadPlanner';

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
  const plannerRef = useRef(createKLineRangePreloadPlanner());

  latestRef.current = {
    candlesLength,
    offset,
    onRequestRange,
    total,
  };

  useEffect(() => {
    plannerRef.current.reset();
  }, [offset, resetKey, total]);

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

      const request = plannerRef.current.next({
        candlesLength: loadedLength,
        offset: loadedOffset,
        range,
        total: currentTotal,
      });
      if (!request) return;

      requestRange(request.left, request.right);
    },
    [suppressRef],
  );
}
