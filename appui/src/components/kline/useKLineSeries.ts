import { useEffect, useRef, type MutableRefObject } from 'react';
import {
  CandlestickSeries,
  HistogramSeries,
  LineSeries,
  createSeriesMarkers,
  type IChartApi,
  type ISeriesApi,
  type SeriesMarker,
  type Time,
} from 'lightweight-charts';

import { CHART_PALETTE, CHART_THEME, type ThemeMode } from '../../config/theme';
import type { CandleColorScheme } from '../../store/configSlice';

export interface MarkerApi {
  setMarkers: (markers: SeriesMarker<Time>[]) => void;
}

export interface KLineSeriesRefs {
  candleSeriesRef: MutableRefObject<ISeriesApi<'Candlestick'> | null>;
  markerApiRef: MutableRefObject<MarkerApi | null>;
  maSeriesRef: MutableRefObject<ISeriesApi<'Line'> | null>;
  volumeSeriesRef: MutableRefObject<ISeriesApi<'Histogram'> | null>;
}

interface UseKLineSeriesParams {
  chartRef: MutableRefObject<IChartApi | null>;
  colorScheme: CandleColorScheme;
  maColor: string;
  maVisible: boolean;
  themeMode: ThemeMode;
}

export function useKLineSeries({
  chartRef,
  colorScheme,
  maColor,
  maVisible,
  themeMode,
}: UseKLineSeriesParams): KLineSeriesRefs {
  const candleSeriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null);
  const volumeSeriesRef = useRef<ISeriesApi<'Histogram'> | null>(null);
  const maSeriesRef = useRef<ISeriesApi<'Line'> | null>(null);
  const markerApiRef = useRef<MarkerApi | null>(null);
  const initialOptionsRef = useRef({ colorScheme, maColor, maVisible, themeMode });

  useEffect(() => {
    const chart = chartRef.current;
    if (!chart) return undefined;

    const colors = CHART_PALETTE[initialOptionsRef.current.colorScheme];
    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: colors.up,
      downColor: colors.down,
      wickUpColor: colors.up,
      wickDownColor: colors.down,
      borderVisible: false,
      priceLineColor: CHART_THEME[initialOptionsRef.current.themeMode].priceLine,
      lastValueVisible: true,
    });

    const maSeries = chart.addSeries(LineSeries, {
      color: initialOptionsRef.current.maColor,
      lineWidth: 2,
      priceLineVisible: false,
      lastValueVisible: false,
      visible: initialOptionsRef.current.maVisible,
    });

    const volumeSeries = chart.addSeries(HistogramSeries, {
      priceFormat: {
        type: 'volume',
      },
      priceScaleId: '',
      lastValueVisible: false,
      priceLineVisible: false,
    });
    chart.priceScale('').applyOptions({
      scaleMargins: {
        top: 0.82,
        bottom: 0,
      },
    });

    candleSeriesRef.current = candleSeries;
    volumeSeriesRef.current = volumeSeries;
    maSeriesRef.current = maSeries;
    markerApiRef.current = createSeriesMarkers(candleSeries, []);

    return () => {
      candleSeriesRef.current = null;
      volumeSeriesRef.current = null;
      maSeriesRef.current = null;
      markerApiRef.current = null;
    };
  }, [chartRef]);

  useEffect(() => {
    const colors = CHART_PALETTE[colorScheme];
    candleSeriesRef.current?.applyOptions({
      upColor: colors.up,
      downColor: colors.down,
      wickUpColor: colors.up,
      wickDownColor: colors.down,
    });
  }, [colorScheme]);

  useEffect(() => {
    maSeriesRef.current?.applyOptions({ color: maColor, visible: maVisible });
  }, [maColor, maVisible]);

  useEffect(() => {
    candleSeriesRef.current?.applyOptions({
      priceLineColor: CHART_THEME[themeMode].priceLine,
    });
  }, [themeMode]);

  return {
    candleSeriesRef,
    markerApiRef,
    maSeriesRef,
    volumeSeriesRef,
  };
}
