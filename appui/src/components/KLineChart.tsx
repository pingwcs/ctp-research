import BellOutlined from '@ant-design/icons/BellOutlined';
import ThunderboltOutlined from '@ant-design/icons/ThunderboltOutlined';
import Button from 'antd/es/button';
import { useMemo, useRef, type CSSProperties } from 'react';
import Empty from 'antd/es/empty';
import Tooltip from 'antd/es/tooltip';

import type { Candle, TradeMarker } from '../api/market';
import type { ChartViewportConfig } from '../config/responsive';
import type { CandleColorScheme, Language, PriceScale } from '../store/configSlice';
import type { ThemeMode } from '../config/theme';
import { useKLineRangePreload } from '../hooks/useKLineRangePreload';
import ChartTitle from './kline/ChartTitle';
import { formatChartNumber } from './kline/data';
import { useKLineDataSync } from './kline/useKLineDataSync';
import { useKLineSeries } from './kline/useKLineSeries';
import { useLightweightChart } from './kline/useLightweightChart';

interface KLineChartProps {
  activePeriod?: string;
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
  themeMode: ThemeMode;
}

interface ChartAnnotation {
  label: string;
  value: string;
  className: string;
  style: CSSProperties;
}

function clamp(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value));
}

function getPriceTop(price: number, high: number, low: number) {
  const range = high - low || Math.max(1, Math.abs(high));
  return clamp(((high - price) / range) * 70 + 10, 8, 82);
}

function buildChartInsights(candles: Candle[], language: Language) {
  if (!candles.length) {
    return {
      annotations: [] as ChartAnnotation[],
      currentPrice: null as { value: string; top: number } | null,
    };
  }

  const recent = candles.slice(-160);
  const high = recent.reduce((max, item) => Math.max(max, item.high), recent[0].high);
  const low = recent.reduce((min, item) => Math.min(min, item.low), recent[0].low);
  const range = high - low || Math.max(1, Math.abs(high));
  const latest = candles[candles.length - 1];
  const resistance = high - range * 0.22;
  const support = low + range * 0.24;

  return {
    annotations: [
      {
        label: 'Peak',
        value: formatChartNumber(high, language),
        className: 'chart-note chart-note--peak',
        style: { left: '64%', top: `${getPriceTop(high, high, low)}%` },
      },
      {
        label: 'Resist',
        value: formatChartNumber(resistance, language),
        className: 'chart-note chart-note--resist',
        style: { left: '78%', top: `${getPriceTop(resistance, high, low)}%` },
      },
      {
        label: 'Support',
        value: formatChartNumber(support, language),
        className: 'chart-note chart-note--support',
        style: { left: '18%', top: `${getPriceTop(support, high, low)}%` },
      },
      {
        label: 'Low',
        value: formatChartNumber(low, language),
        className: 'chart-note chart-note--low',
        style: { left: '31%', top: `${getPriceTop(low, high, low)}%` },
      },
    ],
    currentPrice: {
      value: formatChartNumber(latest.close, language),
      top: getPriceTop(latest.close, high, low),
    },
  };
}

export default function KLineChart({
  activePeriod = '5m',
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
  themeMode,
}: KLineChartProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const tooltipRef = useRef<HTMLDivElement | null>(null);
  const candleMapRef = useRef<Map<number, Candle>>(new Map());
  const handlerSuppressedRef = useRef(false);
  const handleVisibleRangeChange = useKLineRangePreload({
    candlesLength: candles.length,
    offset,
    onRequestRange,
    resetKey: symbol,
    suppressRef: handlerSuppressedRef,
    total,
  });
  const { chartRef, resetTimeScale } = useLightweightChart({
    candleMapRef,
    containerRef,
    language,
    onVisibleRangeChange: handleVisibleRangeChange,
    priceScale,
    themeMode,
    tooltipRef,
  });
  const seriesRefs = useKLineSeries({
    chartRef,
    colorScheme,
    maColor,
    maVisible,
    themeMode,
  });

  useKLineDataSync({
    ...seriesRefs,
    candleMapRef,
    candles,
    chartRef,
    colorScheme,
    handlerSuppressedRef,
    maVisible,
    maWindow,
    markers,
    offset,
  });

  const chartStyle = useMemo<CSSProperties>(
    () => ({
      height: chartViewport?.height,
      maxHeight: chartViewport?.maxHeight ?? '100%',
      maxWidth: chartViewport?.maxWidth ?? '100%',
      width: '100%',
    }),
    [chartViewport],
  );
  const chartInsights = useMemo(
    () => buildChartInsights(candles, language),
    [candles, language],
  );

  return (
    <div className="chart-shell" style={chartStyle}>
      <ChartTitle
        activePeriod={activePeriod}
        candlesCount={candles.length}
        maVisible={maVisible}
        maWindow={maWindow}
        offset={offset}
        onResetTimeScale={resetTimeScale}
        symbol={symbol}
        total={total}
      />
      <div className="chart-stage" ref={containerRef}>
        <div className="chart-tooltip" ref={tooltipRef} />
        {chartInsights.annotations.length ? (
          <div aria-hidden className="chart-annotations">
            {chartInsights.annotations.map((item) => (
              <span className={item.className} key={item.label} style={item.style}>
                <strong>{item.label}</strong>
                <small>{item.value}</small>
              </span>
            ))}
          </div>
        ) : null}
        {chartInsights.currentPrice ? (
          <span
            aria-hidden
            className="current-price-badge"
            style={{ top: `${chartInsights.currentPrice.top}%` }}
          >
            {chartInsights.currentPrice.value}
          </span>
        ) : null}
        <div className="chart-floating-actions">
          <Tooltip title="Create alert" placement="left">
            <Button aria-label="Create alert" icon={<BellOutlined />} shape="circle" />
          </Tooltip>
          <Tooltip title="Quick signal" placement="left">
            <Button aria-label="Quick signal" icon={<ThunderboltOutlined />} shape="circle" />
          </Tooltip>
        </div>
        {!candles.length && !loading ? (
          <div className="chart-empty">
            <Empty description="No market data" image={Empty.PRESENTED_IMAGE_SIMPLE} />
          </div>
        ) : null}
      </div>
    </div>
  );
}
