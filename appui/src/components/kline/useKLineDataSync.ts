import { useEffect, useMemo, useRef, type MutableRefObject } from 'react';
import type { IChartApi } from 'lightweight-charts';

import type { Candle, TradeMarker } from '../../api/market';
import type { CandleColorScheme } from '../../store/configSlice';
import { toCandleData, toMaData, toSeriesMarkers, toVolumeData } from './data';
import type { KLineSeriesRefs } from './useKLineSeries';

interface UseKLineDataSyncParams extends KLineSeriesRefs {
  candleMapRef: MutableRefObject<Map<number, Candle>>;
  candles: Candle[];
  chartRef: MutableRefObject<IChartApi | null>;
  colorScheme: CandleColorScheme;
  handlerSuppressedRef: MutableRefObject<boolean>;
  maVisible: boolean;
  maWindow: number;
  markers: TradeMarker[];
  offset: number;
}

type SyncMode = 'append' | 'replace' | 'update';

interface SyncSnapshot {
  candles: Candle[];
  colorScheme: CandleColorScheme;
  maVisible: boolean;
  maWindow: number;
  offset: number;
}

function captureGlobalRange(
  chart: IChartApi | null,
  offset: number,
): { left: number; right: number } | null {
  const logical = chart?.timeScale().getVisibleLogicalRange();
  if (!logical) return null;
  return { left: offset + Math.floor(logical.from), right: offset + Math.ceil(logical.to) };
}

function areCandlesEqual(left: Candle, right: Candle) {
  return (
    left.time === right.time &&
    left.open === right.open &&
    left.high === right.high &&
    left.low === right.low &&
    left.close === right.close &&
    left.volume === right.volume
  );
}

function hasSamePrefix(left: Candle[], right: Candle[], endExclusive: number) {
  for (let index = 0; index < endExclusive; index += 1) {
    if (!areCandlesEqual(left[index], right[index])) return false;
  }
  return true;
}

function getSyncMode(previous: SyncSnapshot | null, next: SyncSnapshot): SyncMode {
  if (
    !previous ||
    previous.offset !== next.offset ||
    previous.colorScheme !== next.colorScheme ||
    previous.maVisible !== next.maVisible ||
    previous.maWindow !== next.maWindow ||
    !next.candles.length
  ) {
    return 'replace';
  }

  if (
    next.candles.length === previous.candles.length + 1 &&
    hasSamePrefix(previous.candles, next.candles, previous.candles.length)
  ) {
    return 'append';
  }

  if (
    next.candles.length === previous.candles.length &&
    hasSamePrefix(previous.candles, next.candles, Math.max(0, next.candles.length - 1))
  ) {
    return 'update';
  }

  return 'replace';
}

function syncCandleMap(
  candleMapRef: MutableRefObject<Map<number, Candle>>,
  candles: Candle[],
  mode: SyncMode,
) {
  if ((mode === 'append' || mode === 'update') && candles.length) {
    const lastCandle = candles[candles.length - 1];
    candleMapRef.current.set(lastCandle.time, lastCandle);
    return;
  }

  candleMapRef.current = new Map(candles.map((item) => [item.time, item]));
}

export function useKLineDataSync({
  candleMapRef,
  candles,
  candleSeriesRef,
  chartRef,
  colorScheme,
  handlerSuppressedRef,
  maSeriesRef,
  maVisible,
  maWindow,
  markerApiRef,
  markers,
  offset,
  volumeSeriesRef,
}: UseKLineDataSyncParams) {
  const previousSnapshotRef = useRef<SyncSnapshot | null>(null);
  const previousMarkersRef = useRef<TradeMarker[] | null>(null);
  const suppressionReleaseTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const candleData = useMemo(() => toCandleData(candles), [candles]);
  const volumeData = useMemo(() => toVolumeData(candles, colorScheme), [candles, colorScheme]);
  const maData = useMemo(
    () => (maVisible ? toMaData(candles, maWindow) : []),
    [candles, maVisible, maWindow],
  );
  const markerData = useMemo(() => toSeriesMarkers(markers), [markers]);

  useEffect(
    () => () => {
      if (suppressionReleaseTimerRef.current) {
        clearTimeout(suppressionReleaseTimerRef.current);
      }
    },
    [],
  );

  useEffect(() => {
    if (
      !candleSeriesRef.current ||
      !volumeSeriesRef.current ||
      !maSeriesRef.current ||
      !markerApiRef.current
    ) {
      return;
    }

    const chart = chartRef.current;
    const previousSnapshot = previousSnapshotRef.current;
    const nextSnapshot = {
      candles,
      colorScheme,
      maVisible,
      maWindow,
      offset,
    };
    const mode = getSyncMode(previousSnapshot, nextSnapshot);
    const previousGlobalRange = captureGlobalRange(chart, previousSnapshot?.offset ?? offset);
    const lastIndex = candles.length - 1;

    syncCandleMap(candleMapRef, candles, mode);
    if (suppressionReleaseTimerRef.current) {
      clearTimeout(suppressionReleaseTimerRef.current);
      suppressionReleaseTimerRef.current = null;
    }
    handlerSuppressedRef.current = true;
    try {
      if (mode === 'replace') {
        candleSeriesRef.current.setData(candleData);
        volumeSeriesRef.current.setData(volumeData);
        maSeriesRef.current.setData(maData);
      } else if (lastIndex >= 0) {
        candleSeriesRef.current.update(candleData[lastIndex]);
        volumeSeriesRef.current.update(volumeData[lastIndex]);
        if (maVisible && maData[lastIndex]) {
          maSeriesRef.current.update(maData[lastIndex]);
        }
      }

      if (previousMarkersRef.current !== markers) {
        markerApiRef.current.setMarkers(markerData);
        previousMarkersRef.current = markers;
      }

      if (chart && previousGlobalRange && previousSnapshot?.offset !== offset) {
        const newFrom = Math.max(0, previousGlobalRange.left - offset);
        const newTo = Math.min(candles.length - 1, previousGlobalRange.right - offset);
        if (newFrom < newTo && newFrom < candles.length) {
          chart.timeScale().setVisibleLogicalRange({ from: newFrom, to: newTo });
        }
      }
    } finally {
      suppressionReleaseTimerRef.current = setTimeout(() => {
        handlerSuppressedRef.current = false;
        suppressionReleaseTimerRef.current = null;
      }, 0);
    }

    previousSnapshotRef.current = nextSnapshot;
  }, [
    candleData,
    candleMapRef,
    candleSeriesRef,
    candles,
    chartRef,
    colorScheme,
    handlerSuppressedRef,
    maData,
    maSeriesRef,
    maVisible,
    maWindow,
    markerApiRef,
    markerData,
    markers,
    offset,
    volumeData,
    volumeSeriesRef,
  ]);
}
