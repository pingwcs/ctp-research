import { useEffect, useMemo, useRef } from 'react';
import {
  CandlestickSeries,
  ColorType,
  CrosshairMode,
  HistogramSeries,
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

import type { Candle, TradeMarker } from '../store/marketSlice';

interface KLineChartProps {
  candles: Candle[];
  markers: TradeMarker[];
  loading: boolean;
  symbol: string;
}

interface Point {
  x: number;
  y: number;
}

interface MarkerApi {
  setMarkers: (markers: SeriesMarker<Time>[]) => void;
}

const numberFormatter = new Intl.NumberFormat('zh-CN', {
  maximumFractionDigits: 4,
});

const volumeFormatter = new Intl.NumberFormat('zh-CN', {
  maximumFractionDigits: 0,
});

function toUtcTimestamp(time: number): UTCTimestamp {
  return time as UTCTimestamp;
}

function formatTime(time: number) {
  return new Date(time * 1000).toLocaleString('zh-CN', {
    hour12: false,
  });
}

function renderTooltip(
  tooltip: HTMLDivElement | null,
  candle: Candle | undefined,
  point: Point | null,
  container: HTMLDivElement | null,
) {
  if (!tooltip || !candle || !point || !container) return;

  const toneClass = candle.close >= candle.open ? 'is-up' : 'is-down';
  tooltip.className = `chart-tooltip ${toneClass}`;
  tooltip.innerHTML = `
    <div class="chart-tooltip__time">${formatTime(candle.time)}</div>
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

function toVolumeData(candles: Candle[]): HistogramData<UTCTimestamp>[] {
  return candles.map((item) => ({
    time: toUtcTimestamp(item.time),
    value: item.volume,
    color: item.close >= item.open ? 'rgba(22, 163, 74, 0.35)' : 'rgba(220, 38, 38, 0.35)',
  }));
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

export default function KLineChart({ candles, markers, loading, symbol }: KLineChartProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const tooltipRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candleSeriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null);
  const volumeSeriesRef = useRef<ISeriesApi<'Histogram'> | null>(null);
  const markersRef = useRef<MarkerApi | null>(null);
  const candleMapRef = useRef<Map<number, Candle>>(new Map());

  const candleData = useMemo(() => toCandleData(candles), [candles]);
  const volumeData = useMemo(() => toVolumeData(candles), [candles]);
  const markerData = useMemo(() => toSeriesMarkers(markers), [markers]);

  useEffect(() => {
    if (!containerRef.current) return undefined;

    const container = containerRef.current;
    const chart = createChart(container, {
      autoSize: true,
      layout: {
        background: { type: ColorType.Solid, color: '#09090b' },
        textColor: '#d4d4d8',
        fontFamily: 'Inter, ui-sans-serif, system-ui, sans-serif',
      },
      localization: {
        locale: 'zh-CN',
        priceFormatter: (price: number) => numberFormatter.format(price),
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
        scaleMargins: {
          top: 0.08,
          bottom: 0.24,
        },
      },
      timeScale: {
        borderColor: '#27272a',
        timeVisible: true,
        secondsVisible: false,
        rightOffset: 8,
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

    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: '#16a34a',
      downColor: '#dc2626',
      wickUpColor: '#22c55e',
      wickDownColor: '#ef4444',
      borderVisible: false,
      priceLineColor: '#0891b2',
      lastValueVisible: true,
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

    const markerApi = createSeriesMarkers(candleSeries, []);

    const onCrosshairMove = (param: MouseEventParams<Time>) => {
      if (!param.point || !param.time || param.point.x < 0 || param.point.y < 0) {
        hideTooltip(tooltipRef.current);
        return;
      }

      const candle = candleMapRef.current.get(Number(param.time));
      if (!candle) {
        hideTooltip(tooltipRef.current);
        return;
      }

      renderTooltip(tooltipRef.current, candle, param.point, containerRef.current);
    };

    chart.subscribeCrosshairMove(onCrosshairMove);

    chartRef.current = chart;
    candleSeriesRef.current = candleSeries;
    volumeSeriesRef.current = volumeSeries;
    markersRef.current = markerApi;

    return () => {
      chart.unsubscribeCrosshairMove(onCrosshairMove);
      markerApi.setMarkers([]);
      chart.remove();
      chartRef.current = null;
      candleSeriesRef.current = null;
      volumeSeriesRef.current = null;
      markersRef.current = null;
    };
  }, []);

  useEffect(() => {
    candleMapRef.current = new Map(candles.map((item) => [item.time, item]));
    if (!candleSeriesRef.current || !volumeSeriesRef.current || !markersRef.current) return;

    candleSeriesRef.current.setData(candleData);
    volumeSeriesRef.current.setData(volumeData);
    markersRef.current.setMarkers(markerData);

    if (candles.length) {
      chartRef.current?.timeScale().fitContent();
    }
  }, [candles, candleData, volumeData, markerData]);

  return (
    <div className="chart-shell">
      <div className="chart-title">
        <div>
          <span className="chart-title__symbol">{symbol}</span>
          <span className="chart-title__meta">5min OHLCV</span>
        </div>
        <span className="chart-title__status">{loading ? 'Loading' : `${candles.length} bars`}</span>
      </div>
      <div className="chart-stage" ref={containerRef}>
        <div className="chart-tooltip" ref={tooltipRef} />
        {!candles.length && !loading ? <div className="chart-empty">No market data</div> : null}
        {loading ? <div className="chart-loading">Loading</div> : null}
      </div>
    </div>
  );
}
