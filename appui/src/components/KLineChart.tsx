import { useEffect, useMemo, useRef, type CSSProperties } from 'react';
import { Empty, Spin, Typography } from 'antd';
import {
  CandlestickSeries,
  ColorType,
  CrosshairMode,
  HistogramSeries,
  LineSeries,
  PriceScaleMode,
  createChart,
  createSeriesMarkers,
  type CandlestickData,
  type HistogramData,
  type IChartApi,
  type ISeriesApi,
  type MouseEventParams,
  type SeriesMarker,
  type Time,
  type UTCTimestamp,
} from 'lightweight-charts';

import type { Candle, TradeMarker } from '../api/market';
import {
  CHART_TIME_ZONE,
  INITIAL_VISIBLE_BARS,
  MAX_VISIBLE_BARS,
  NUMBER_FORMAT_OPTIONS,
  VOLUME_FORMAT_OPTIONS,
} from '../config/chart';
import type { ChartViewportConfig } from '../config/responsive';
import { CHART_PALETTE } from '../config/theme';
import type { CandleColorScheme, Language, PriceScale } from '../store/configSlice';

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
  maWindow: number;
  maColor: string;
  chartViewport?: ChartViewportConfig;
  onRequestRange?: (left: number, right: number) => void;
}

interface Point {
  x: number;
  y: number;
}

interface MarkerApi {
  setMarkers: (markers: SeriesMarker<Time>[]) => void;
}

interface LogicalRangeLike {
  from: number;
  to: number;
}

interface ChartSeriesBundle {
  candleSeries: ISeriesApi<'Candlestick'>;
  volumeSeries: ISeriesApi<'Histogram'>;
  maSeries: ISeriesApi<'Line'>;
  markerApi: MarkerApi;
}

interface RefBox<T> {
  current: T;
}

const numberFormatter = new Intl.NumberFormat('zh-CN', NUMBER_FORMAT_OPTIONS);
const volumeFormatter = new Intl.NumberFormat('zh-CN', VOLUME_FORMAT_OPTIONS);

function toUtcTimestamp(time: number): UTCTimestamp {
  return time as UTCTimestamp;
}

function formatTime(time: number, language: Language) {
  return new Date(time * 1000).toLocaleString(language, {
    hour12: false,
    timeZone: CHART_TIME_ZONE,
  });
}

function renderTooltip(
  tooltip: HTMLDivElement | null,
  candle: Candle | undefined,
  point: Point | null,
  container: HTMLDivElement | null,
  language: Language,
) {
  if (!tooltip || !candle || !point || !container) return;

  const toneClass = candle.close >= candle.open ? 'is-up' : 'is-down';
  tooltip.className = `chart-tooltip ${toneClass}`;
  tooltip.innerHTML = `
    <div class="chart-tooltip__time">${formatTime(candle.time, language)}</div>
    <div class="chart-tooltip__grid">
      <span>Open</span><strong>${numberFormatter.format(candle.open)}</strong>
      <span>High</span><strong>${numberFormatter.format(candle.high)}</strong>
      <span>Low</span><strong>${numberFormatter.format(candle.low)}</strong>
      <span>Close</span><strong>${numberFormatter.format(candle.close)}</strong>
      <span>Vol</span><strong>${volumeFormatter.format(candle.volume)}</strong>
    </div>
  `;

  const { width, height } = container.getBoundingClientRect();
  const tooltipWidth = tooltip.offsetWidth || 190;
  const tooltipHeight = tooltip.offsetHeight || 132;
  const left = Math.min(Math.max(point.x + 16, 8), width - tooltipWidth - 8);
  const top = Math.min(Math.max(point.y + 16, 8), height - tooltipHeight - 8);

  tooltip.style.transform = `translate(${left}px, ${top}px)`;
  tooltip.style.opacity = '1';
}

function hideTooltip(tooltip: HTMLDivElement | null) {
  if (tooltip) {
    tooltip.style.opacity = '0';
  }
}

function toCandleData(candles: Candle[]): CandlestickData<UTCTimestamp>[] {
  return candles.map((item) => ({
    time: toUtcTimestamp(item.time),
    open: item.open,
    high: item.high,
    low: item.low,
    close: item.close,
  }));
}

function toVolumeData(
  candles: Candle[],
  colorScheme: CandleColorScheme,
): HistogramData<UTCTimestamp>[] {
  const colors = CHART_PALETTE[colorScheme];
  return candles.map((item) => ({
    time: toUtcTimestamp(item.time),
    value: item.volume,
    color: item.close >= item.open ? colors.upVolume : colors.downVolume,
  }));
}

function toMaData(candles: Candle[], windowSize: number) {
  return candles.map((item, index) => {
    const start = Math.max(0, index - windowSize + 1);
    const sample = candles.slice(start, index + 1);
    const value = sample.reduce((sum, candle) => sum + candle.close, 0) / sample.length;
    return {
      time: toUtcTimestamp(item.time),
      value,
    };
  });
}

function toSeriesMarkers(markers: TradeMarker[]): SeriesMarker<Time>[] {
  return markers.map((item) => ({
    time: toUtcTimestamp(item.time),
    position: item.position,
    color: item.color,
    shape: item.shape,
    text: item.text,
  }));
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
      priceFormatter: (price: number) => numberFormatter.format(price),
      timeFormatter: (time: Time) => formatTime(Number(time), language),
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
        top: 0.08,
        bottom: 0.24,
      },
    },
    timeScale: {
      borderColor: '#27272a',
      timeVisible: true,
      secondsVisible: false,
      rightOffset: 4,
      barSpacing: 8,
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

function createCrosshairHandler(
  tooltipRef: RefBox<HTMLDivElement | null>,
  candleMapRef: RefBox<Map<number, Candle>>,
  containerRef: RefBox<HTMLDivElement | null>,
  languageRef: RefBox<Language>,
) {
  return (param: MouseEventParams<Time>) => {
    if (!param.point || !param.time || param.point.x < 0 || param.point.y < 0) {
      hideTooltip(tooltipRef.current);
      return;
    }

    const candle = candleMapRef.current.get(Number(param.time));
    if (!candle) {
      hideTooltip(tooltipRef.current);
      return;
    }

    renderTooltip(
      tooltipRef.current,
      candle,
      param.point,
      containerRef.current,
      languageRef.current,
    );
  };
}

function createVisibleRangeHandler(
  chart: IChartApi,
  offsetRef: RefBox<number>,
  totalRef: RefBox<number>,
  rangeCallbackRef: RefBox<((left: number, right: number) => void) | undefined>,
  maxVisibleBars: number,
) {
  let lastEmittedRangeKey = '';

  return (range: LogicalRangeLike | null) => {
    if (!range) return;

    const localLeft = Math.floor(range.from);
    const localRight = Math.ceil(range.to);
    const visibleBars = localRight - localLeft + 1;

    if (visibleBars > maxVisibleBars) {
      chart.timeScale().setVisibleLogicalRange({
        from: range.to - maxVisibleBars + 1,
        to: range.to,
      });
      return;
    }

    const currentOffset = offsetRef.current;
    const currentTotal = totalRef.current;
    const globalLeft = currentOffset + localLeft;
    const globalRight = currentOffset + localRight;

    if (currentTotal > 0 && (globalLeft < 0 || globalRight >= currentTotal)) {
      chart.timeScale().setVisibleLogicalRange({
        from: Math.max(0 - currentOffset, range.from),
        to: Math.min(currentTotal - 1 - currentOffset, range.to),
      });
      return;
    }

    const rangeKey = `${globalLeft}:${globalRight}`;
    if (rangeKey === lastEmittedRangeKey) {
      return;
    }
    lastEmittedRangeKey = rangeKey;

    rangeCallbackRef.current?.(globalLeft, globalRight);
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
  const rangeCallbackRef = useRef(onRequestRange);
  const offsetRef = useRef(offset);
  const totalRef = useRef(total);
  const languageRef = useRef(language);
  const initialRangeAppliedRef = useRef(false);

  rangeCallbackRef.current = onRequestRange;
  offsetRef.current = offset;
  totalRef.current = total;
  languageRef.current = language;

  const candleData = useMemo(() => toCandleData(candles), [candles]);
  const volumeData = useMemo(() => toVolumeData(candles, colorScheme), [candles, colorScheme]);
  const maData = useMemo(() => toMaData(candles, maWindow), [candles, maWindow]);
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

  useEffect(() => {
    if (!containerRef.current) return undefined;

    const chart = createBaseChart(containerRef.current, language, priceScale);
    const { candleSeries, volumeSeries, maSeries, markerApi } = createChartSeries(
      chart,
      colorScheme,
      maColor,
    );
    const onCrosshairMove = createCrosshairHandler(
      tooltipRef,
      candleMapRef,
      containerRef,
      languageRef,
    );
    const onVisibleRangeChange = createVisibleRangeHandler(
      chart,
      offsetRef,
      totalRef,
      rangeCallbackRef,
      MAX_VISIBLE_BARS,
    );

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
  }, []);

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
        priceFormatter: (price: number) => numberFormatter.format(price),
        timeFormatter: (time: Time) => formatTime(Number(time), language),
      },
    });
  }, [language]);

  useEffect(() => {
    maSeriesRef.current?.applyOptions({ color: maColor });
  }, [maColor]);

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

    candleSeriesRef.current.setData(candleData);
    volumeSeriesRef.current.setData(volumeData);
    maSeriesRef.current.setData(maData);
    markersRef.current.setMarkers(markerData);

    if (candles.length && !initialRangeAppliedRef.current) {
      const to = candles.length - 1;
      chartRef.current?.timeScale().setVisibleLogicalRange({
        from: Math.max(0, to - INITIAL_VISIBLE_BARS + 1),
        to,
      });
      initialRangeAppliedRef.current = true;
    }
  }, [candles, candleData, volumeData, maData, markerData]);

  return (
    <div className="chart-shell" style={chartStyle}>
      <div className="chart-title">
        <div>
          <Typography.Text className="chart-title__symbol">{symbol}</Typography.Text>
          <Typography.Text className="chart-title__meta" type="secondary">
            5min OHLCV · {offset + 1}-{offset + candles.length} / {total || candles.length}
          </Typography.Text>
        </div>
        <Typography.Text className="chart-title__status" type="secondary">
          {loading ? 'Loading' : `${candles.length} bars · MA${maWindow}`}
        </Typography.Text>
      </div>
      <div className="chart-stage" ref={containerRef}>
        <div className="chart-tooltip" ref={tooltipRef} />
        {!candles.length && !loading ? (
          <div className="chart-empty">
            <Empty description="No market data" image={Empty.PRESENTED_IMAGE_SIMPLE} />
          </div>
        ) : null}
        {loading ? (
          <div className="chart-loading">
            <Spin tip="Loading" />
          </div>
        ) : null}
      </div>
    </div>
  );
}
