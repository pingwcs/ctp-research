import { useCallback, useEffect, useMemo, useRef } from 'react';
import throttle from 'lodash/throttle';

import type { KLineRequest } from '../../api/market';
import { CHART_RANGE_THROTTLE_MS, DEFAULT_KLINE_LIMIT } from '../../config/chart';
import { fetchKLineData, setSymbol } from '../../store/marketSlice';
import { useAppDispatch } from '../../store';

interface RangeRequestSnapshot {
  symbol: string;
  total: number;
  loading: boolean;
  lastRequestedRange: string | null;
}

interface AbortableRequest extends Promise<unknown> {
  abort: () => void;
}

function normalizeSymbol(symbol: string) {
  return symbol.trim().toUpperCase();
}

function getRequestKey(request: KLineRequest) {
  const symbol = normalizeSymbol(request.symbol);
  const offset = request.offset ?? 'latest';
  const limit = request.limit ?? DEFAULT_KLINE_LIMIT;
  return `${symbol}:${offset}:${limit}`;
}

export function useKLineRangeRequests({
  lastRequestedRange,
  loading,
  symbol,
  total,
}: RangeRequestSnapshot) {
  const dispatch = useAppDispatch();
  const activeRequestRef = useRef<AbortableRequest | null>(null);
  const activeRequestKeyRef = useRef<string | null>(null);
  const scheduledAbortRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const initialSymbolRef = useRef(symbol);
  const pendingRangeRef = useRef<string | null>(null);
  const rangeRequestInFlightRef = useRef(false);
  const requestStateRef = useRef<RangeRequestSnapshot>({
    symbol,
    total,
    loading,
    lastRequestedRange,
  });

  const resetRangeTracking = useCallback(() => {
    pendingRangeRef.current = null;
    rangeRequestInFlightRef.current = false;
  }, []);

  const cancelScheduledAbort = useCallback(() => {
    if (scheduledAbortRef.current) {
      clearTimeout(scheduledAbortRef.current);
      scheduledAbortRef.current = null;
    }
  }, []);

  const abortActiveRequest = useCallback(() => {
    cancelScheduledAbort();
    activeRequestRef.current?.abort();
    activeRequestRef.current = null;
    activeRequestKeyRef.current = null;
  }, [cancelScheduledAbort]);

  const scheduleAbortActiveRequest = useCallback(() => {
    if (!activeRequestRef.current) return;

    cancelScheduledAbort();
    scheduledAbortRef.current = setTimeout(() => {
      scheduledAbortRef.current = null;
      abortActiveRequest();
    }, 0);
  }, [abortActiveRequest, cancelScheduledAbort]);

  const dispatchFetch = useCallback(
    (request: KLineRequest, shouldAbortActive = false) => {
      const requestKey = getRequestKey(request);
      cancelScheduledAbort();

      if (activeRequestRef.current && activeRequestKeyRef.current === requestKey) {
        return activeRequestRef.current;
      }

      if (shouldAbortActive) {
        abortActiveRequest();
      }

      const promise = dispatch(fetchKLineData(request));
      activeRequestRef.current = promise;
      activeRequestKeyRef.current = requestKey;
      void promise.finally(() => {
        if (activeRequestRef.current === promise) {
          activeRequestRef.current = null;
          activeRequestKeyRef.current = null;
        }
      });
      return promise;
    },
    [abortActiveRequest, cancelScheduledAbort, dispatch],
  );

  useEffect(() => {
    const initialRequest = { symbol: initialSymbolRef.current, limit: DEFAULT_KLINE_LIMIT };
    void dispatchFetch(initialRequest, true);
  }, [dispatchFetch]);

  useEffect(() => {
    requestStateRef.current = {
      symbol,
      total,
      loading,
      lastRequestedRange,
    };
  }, [lastRequestedRange, loading, symbol, total]);

  useEffect(() => {
    if (!loading) {
      rangeRequestInFlightRef.current = false;
    }
  }, [lastRequestedRange, loading]);

  useEffect(() => () => scheduleAbortActiveRequest(), [scheduleAbortActiveRequest]);

  const loadSymbol = useCallback(
    (draftSymbol: string) => {
      const nextSymbol = normalizeSymbol(draftSymbol);
      if (!nextSymbol) return;

      resetRangeTracking();
      dispatch(setSymbol(nextSymbol));
      void dispatchFetch({ symbol: nextSymbol, limit: DEFAULT_KLINE_LIMIT }, true);
    },
    [dispatch, dispatchFetch, resetRangeTracking],
  );

  const refresh = useCallback(() => {
    resetRangeTracking();
    void dispatchFetch({ symbol, limit: DEFAULT_KLINE_LIMIT }, true);
  }, [dispatchFetch, resetRangeTracking, symbol]);

  const requestRange = useCallback(
    (left: number, right: number) => {
      const state = requestStateRef.current;
      if (!state.total || state.loading || rangeRequestInFlightRef.current) return;

      const requestKey = `${left}:${right - left + 1}`;
      if (pendingRangeRef.current === requestKey || state.lastRequestedRange === requestKey) {
        return;
      }

      pendingRangeRef.current = requestKey;
      rangeRequestInFlightRef.current = true;
      void dispatchFetch({
        symbol: state.symbol,
        offset: left,
        limit: right - left + 1,
      });
    },
    [dispatchFetch],
  );

  const throttledRequestRange = useMemo(
    () => throttle(requestRange, CHART_RANGE_THROTTLE_MS, { trailing: false }),
    [requestRange],
  );

  useEffect(() => () => throttledRequestRange.cancel(), [throttledRequestRange]);

  return {
    loadSymbol,
    refresh,
    throttledRequestRange,
  };
}
