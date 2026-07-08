import { UndoOutlined } from '@ant-design/icons';
import { useCallback, useEffect, useMemo, useRef, type CSSProperties } from 'react';
import { Button, Empty, Tooltip, Typography } from 'antd';
import {
  CandlestickSeries,
  ColorType,
  CrosshairMode,
  HistogramSeries,
  LineSeries,
  PriceScaleMode,
  createChart,
  createSeriesMarkers,
  type IChartApi,
  type ISeriesApi,
  type MouseEventParams,
  type SeriesMarker,
  type Time,
} from 'lightweight-charts';

import type { Candle, TradeMarker } from '../api/market';
import {
  CHART_BAR_SPACING,
  CHART_PRICE_MARGIN_BOTTOM,
  CHART_PRICE_MARGIN_TOP,
  CHART_RIGHT_OFFSET,
  MAX_BAR_SPACING,
  MIN_BAR_SPACING,
} from '../config/chart';
import type { ChartViewportConfig } from '../config/responsive';
import { CHART_PALETTE } from '../config/theme';
import type { CandleColorScheme, Language, PriceScale } from '../store/configSlice';
import {
  formatChartNumber,
  formatChartTime,
  toCandleData,
  toMaData,
  toSeriesMarkers,
  toVolumeData,
} from './kline/data';
import { createKLineCrosshairHandler } from './kline/tooltip';
import { type LogicalRangeLike, useKLineRangePreload } from '../hooks/useKLineRangePreload';

interface KLineChartProps {
  candles: Candle[];
  markers: TradeMarker[];
  loading: boolean;
  symbol: string;
  total: number;
  offset: number;
  language: Language;
  priceScale: PriceScale;
  colorScheme: CandleColorScheme;
  maVisible: boolean;
  maWindow: number;
  maColor: string;
  chartViewport?: ChartViewportConfig;
  onRequestRange?: (left: number, right: number) => void;
}

interface MarkerApi {
  setMarkers: (markers: SeriesMarker<Time>[]) => void;
}

interface ChartSeriesBundle {
  candleSeries: ISeriesApi<'Candlestick'>;
  volumeSeries: ISeriesApi<'Histogram'>;
  maSeries: ISeriesApi<'Line'>;
  markerApi: MarkerApi;
}

function createBaseChart(container: HTMLDivElement, language: Language, priceScale: PriceScale) {
  return createChart(container, {
    autoSize: true,
    layout: {
      background: { type: ColorType.Solid, color: '#09090b' },
      textColor: '#d4d4d8',
      fontFamily: 'Inter, ui-sans-serif, system-ui, sans-serif',
    },
    localization: {
      locale: language,
      priceFormatter: (price: number) => formatChartNumber(price, language),
      timeFormatter: (time: Time) => formatChartTime(Number(time), language),
    },
    grid: {
      vertLines: { color: '#18181b' },
      horzLines: { color: '#18181b' },
    },
    crosshair: {
      mode: CrosshairMode.Normal,
      vertLine: {
        color: '#71717a',
        labelBackgroundColor: '#0e7490',
      },
      horzLine: {
        color: '#71717a',
        labelBackgroundColor: '#0e7490',
      },
    },
    rightPriceScale: {
      borderColor: '#27272a',
      mode: priceScale === 'logarithmic' ? PriceScaleMode.Logarithmic : PriceScaleMode.Normal,
      scaleMargins: {
        top: CHART_PRICE_MARGIN_TOP,
        bottom: CHART_PRICE_MARGIN_BOTTOM,
      },
    },
    timeScale: {
      borderColor: '#27272a',
      timeVisible: true,
      secondsVisible: false,
      rightOffset: CHART_RIGHT_OFFSET,
      barSpacing: CHART_BAR_SPACING,
      minBarSpacing: MIN_BAR_SPACING,
      maxBarSpacing: MAX_BAR_SPACING,
    },
    handleScroll: {
      mouseWheel: true,
      pressedMouseMove: true,
      horzTouchDrag: true,
      vertTouchDrag: false,
    },
    handleScale: {
      axisPressedMouseMove: true,
      mouseWheel: true,
      pinch: true,
    },
  });
}

function createChartSeries(
  chart: IChartApi,
  colorScheme: CandleColorScheme,
  maColor: string,
): ChartSeriesBundle {
  const colors = CHART_PALETTE[colorScheme];
  const candleSeries = chart.addSeries(CandlestickSeries, {
    upColor: colors.up,
    downColor: colors.down,
    wickUpColor: colors.up,
    wickDownColor: colors.down,
    borderVisible: false,
    priceLineColor: '#0891b2',
    lastValueVisible: true,
  });

  const maSeries = chart.addSeries(LineSeries, {
    color: maColor,
    lineWidth: 2,
    priceLineVisible: false,
    lastValueVisible: false,
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

  return {
    candleSeries,
    volumeSeries,
    maSeries,
    markerApi: createSeriesMarkers(candleSeries, []),
  };
}

function disposeChart(
  chart: IChartApi,
  markerApi: MarkerApi,
  onCrosshairMove: (param: MouseEventParams<Time>) => void,
  onVisibleRangeChange: (range: LogicalRangeLike | null) => void,
) {
  chart.unsubscribeCrosshairMove(onCrosshairMove);
  chart.timeScale().unsubscribeVisibleLogicalRangeChange(onVisibleRangeChange);
  markerApi.setMarkers([]);
  chart.remove();
}

function captureGlobalRange(
  chart: IChartApi | null,
  offset: number,
): { left: number; right: number } | null {
  const logical = chart?.timeScale().getVisibleLogicalRange();
  if (!logical) return null;
  return { left: offset + Math.floor(logical.from), right: offset + Math.ceil(logical.to) };
}

export default function KLineChart({
  candles,
  markers,
  loading,
  symbol,
  total,
  offset,
  language,
  priceScale,
  colorScheme,
  maVisible,
  maWindow,
  maColor,
  chartViewport,
  onRequestRange,
}: KLineChartProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const tooltipRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candleSeriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null);
  const volumeSeriesRef = useRef<ISeriesApi<'Histogram'> | null>(null);
  const maSeriesRef = useRef<ISeriesApi<'Line'> | null>(null);
  const markersRef = useRef<MarkerApi | null>(null);
  const candleMapRef = useRef<Map<number, Candle>>(new Map());

  const languageRef = useRef(language);
  // supress handler during setData to avoid intermediate range-change events
  const handlerSuppressedRef = useRef(false);
  const prevOffsetRef = useRef(offset);
  const initialChartOptionsRef = useRef({
    colorScheme,
    language,
    maColor,
    priceScale,
  });

  languageRef.current = language;

  const handleVisibleRangeChange = useKLineRangePreload({
    candlesLength: candles.length,
    offset,
    onRequestRange,
    resetKey: symbol,
    suppressRef: handlerSuppressedRef,
    total,
  });
  const candleData = useMemo(() => toCandleData(candles), [candles]);
  const volumeData = useMemo(() => toVolumeData(candles, colorScheme), [candles, colorScheme]);
  const maData = useMemo(
    () => (maVisible ? toMaData(candles, maWindow) : []),
    [candles, maVisible, maWindow],
  );
  const markerData = useMemo(() => toSeriesMarkers(markers), [markers]);
  const chartStyle = useMemo<CSSProperties>(
    () => ({
      height: chartViewport?.height,
      maxHeight: chartViewport?.maxHeight ?? '100%',
      maxWidth: chartViewport?.maxWidth ?? '100%',
      width: '100%',
    }),
    [chartViewport],
  );
  const resetTimeScale = useCallback(() => {
    chartRef.current?.timeScale().resetTimeScale();
  }, []);

  useEffect(() => {
    if (!containerRef.current) return undefined;

    const {
      colorScheme: initialColorScheme,
      language: initialLanguage,
      maColor: initialMaColor,
      priceScale: initialPriceScale,
    } = initialChartOptionsRef.current;
    const chart = createBaseChart(containerRef.current, initialLanguage, initialPriceScale);
    const { candleSeries, volumeSeries, maSeries, markerApi } = createChartSeries(
      chart,
      initialColorScheme,
      initialMaColor,
    );
    const onCrosshairMove = createKLineCrosshairHandler(
      tooltipRef,
      candleMapRef,
      containerRef,
      languageRef,
    );
    const onVisibleRangeChange = handleVisibleRangeChange;

    chart.subscribeCrosshairMove(onCrosshairMove);
    chart.timeScale().subscribeVisibleLogicalRangeChange(onVisibleRangeChange);

    chartRef.current = chart;
    candleSeriesRef.current = candleSeries;
    volumeSeriesRef.current = volumeSeries;
    maSeriesRef.current = maSeries;
    markersRef.current = markerApi;

    return () => {
      disposeChart(chart, markerApi, onCrosshairMove, onVisibleRangeChange);
      chartRef.current = null;
      candleSeriesRef.current = null;
      volumeSeriesRef.current = null;
      maSeriesRef.current = null;
      markersRef.current = null;
    };
  }, [handleVisibleRangeChange]);

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
    chartRef.current?.priceScale('right').applyOptions({
      mode: priceScale === 'logarithmic' ? PriceScaleMode.Logarithmic : PriceScaleMode.Normal,
    });
  }, [priceScale]);

  useEffect(() => {
    chartRef.current?.applyOptions({
      localization: {
        locale: language,
        priceFormatter: (price: number) => formatChartNumber(price, language),
        timeFormatter: (time: Time) => formatChartTime(Number(time), language),
      },
    });
  }, [language]);

  useEffect(() => {
    maSeriesRef.current?.applyOptions({ color: maColor, visible: maVisible });
  }, [maColor, maVisible]);

  useEffect(() => {
    candleMapRef.current = new Map(candles.map((item) => [item.time, item]));
    if (
      !candleSeriesRef.current ||
      !volumeSeriesRef.current ||
      !maSeriesRef.current ||
      !markersRef.current
    ) {
      return;
    }

    const chart = chartRef.current;
    const oldOffset = prevOffsetRef.current;
    const newOffset = offset;

    // Capture current visible global range before data swap
    const prevGlobalRange = captureGlobalRange(chart, oldOffset);

    // Suppress the range-change handler during setData so it doesn't
    // fire on intermediate logical ranges before we restore the view.
    handlerSuppressedRef.current = true;
    try {
      candleSeriesRef.current.setData(candleData);
      volumeSeriesRef.current.setData(volumeData);
      maSeriesRef.current.setData(maData);
      markersRef.current.setMarkers(markerData);
    } finally {
      handlerSuppressedRef.current = false;
    }

    // Restore visible range at the same global position
    if (chart && prevGlobalRange && oldOffset !== newOffset) {
      const newFrom = Math.max(0, prevGlobalRange.left - newOffset);
      const newTo = Math.min(candles.length - 1, prevGlobalRange.right - newOffset);
      if (newFrom < newTo && newFrom < candles.length) {
        chart.timeScale().setVisibleLogicalRange({ from: newFrom, to: newTo });
      }
    }

    // Always keep prevOffsetRef in sync with current offset
    prevOffsetRef.current = newOffset;
  }, [candles, candleData, volumeData, maData, markerData, offset]);

  return (
    <div className="chart-shell" style={chartStyle}>
      <div className="chart-title">
        <div className="chart-title__main">
          <Typography.Text className="chart-title__symbol">{symbol}</Typography.Text>
          <Typography.Text className="chart-title__meta" type="secondary">
            5min OHLCV . {offset + 1}-{offset + candles.length} / {total || candles.length}
          </Typography.Text>
        </div>
        <div className="chart-title__actions">
          <Typography.Text className="chart-title__status" type="secondary">
            {`${candles.length} bars . ${maVisible ? `MA${maWindow}` : 'MA off'}`}
          </Typography.Text>
          <Tooltip title="Restore zoom">
            <Button
              aria-label="Restore zoom"
              className="chart-icon-button"
              icon={<UndoOutlined />}
              onClick={resetTimeScale}
              size="small"
              type="text"
            />
          </Tooltip>
        </div>
      </div>
      <div className="chart-stage" ref={containerRef}>
        <div className="chart-tooltip" ref={tooltipRef} />
        {!candles.length && !loading ? (
          <div className="chart-empty">
            <Empty description="No market data" image={Empty.PRESENTED_IMAGE_SIMPLE} />
          </div>
        ) : null}
      </div>
    </div>
  );
}
