import { useMemo, useRef, type CSSProperties } from 'react';
import Empty from 'antd/es/empty';

import type { Candle, TradeMarker } from '../api/market';
import type { ChartViewportConfig } from '../config/responsive';
import type { CandleColorScheme, Language, PriceScale } from '../store/configSlice';
import { useKLineRangePreload } from '../hooks/useKLineRangePreload';
import ChartTitle from './kline/ChartTitle';
import { useKLineDataSync } from './kline/useKLineDataSync';
import { useKLineSeries } from './kline/useKLineSeries';
import { useLightweightChart } from './kline/useLightweightChart';

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
    tooltipRef,
  });
  const seriesRefs = useKLineSeries({
    chartRef,
    colorScheme,
    maColor,
    maVisible,
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

  return (
    <div className="chart-shell" style={chartStyle}>
      <ChartTitle
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
        {!candles.length && !loading ? (
          <div className="chart-empty">
            <Empty description="No market data" image={Empty.PRESENTED_IMAGE_SIMPLE} />
          </div>
        ) : null}
      </div>
    </div>
  );
}
