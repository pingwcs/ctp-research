import Empty from 'antd/es/empty';
import { useEffect, useMemo, useRef, useState } from 'react';
import {
  ColorType,
  CrosshairMode,
  LineSeries,
  createChart,
  createSeriesMarkers,
  type IChartApi,
  type ISeriesApi,
  type ISeriesMarkersPluginApi,
  type LineData,
  type MouseEventParams,
  type SeriesMarker,
  type Time,
  type UTCTimestamp,
} from 'lightweight-charts';

import type { BacktestTrade, EquityPoint } from '../api/backtest';
import {
  CHART_BAR_SPACING,
  CHART_PRICE_MARGIN_BOTTOM,
  CHART_PRICE_MARGIN_TOP,
  CHART_RIGHT_OFFSET,
} from '../config/chart';
import { CHART_THEME, type ThemeMode } from '../config/theme';
import { TRADE_MARKER_STYLES } from '../config/tradeMarkers';
import type { Language } from '../store/configSlice';
import { formatChartTime } from './kline/data';

const MONEY_FORMAT_OPTIONS: Intl.NumberFormatOptions = {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
};

interface EquityChartProps {
  language: Language;
  points: EquityPoint[];
  showTradeMarkers?: boolean;
  themeMode: ThemeMode;
  trades?: BacktestTrade[];
}

interface ActiveEquityPoint {
  point: EquityPoint;
  x: number;
  y: number;
}

function toUtcTimestamp(time: number): UTCTimestamp {
  return time as UTCTimestamp;
}

function formatMoney(value: number, language: Language) {
  return new Intl.NumberFormat(language, MONEY_FORMAT_OPTIONS).format(value);
}

function toLineData(points: EquityPoint[]): LineData<Time>[] {
  return [...points]
    .sort((left, right) => left.time - right.time)
    .map((point) => ({
      time: toUtcTimestamp(point.time),
      value: point.equity,
    }));
}

function createTradeMarkers(
  trades: BacktestTrade[],
  language: Language,
): SeriesMarker<Time>[] {
  return trades
    .slice()
    .sort((left, right) => left.time - right.time)
    .map((trade, index) => {
      const style = TRADE_MARKER_STYLES[trade.side];
      return {
        id: `${trade.time}-${trade.side}-${index}`,
        time: toUtcTimestamp(trade.time),
        position: trade.side === 'buy' ? 'belowBar' : 'aboveBar',
        shape: trade.side === 'buy' ? 'arrowUp' : 'arrowDown',
        color: style.color,
        size: 1.2,
        text: `${style.label} ${formatMoney(trade.price, language)}`,
      };
    });
}

function createEquityPointMap(points: EquityPoint[]) {
  return new Map(points.map((point) => [point.time, point]));
}

function createNearestPointLookup(points: EquityPoint[]) {
  const sortedPoints = [...points].sort((left, right) => left.time - right.time);
  return (time: number) => {
    if (!sortedPoints.length) return undefined;

    let low = 0;
    let high = sortedPoints.length - 1;
    while (low < high) {
      const middle = Math.floor((low + high) / 2);
      if (sortedPoints[middle].time < time) {
        low = middle + 1;
      } else {
        high = middle;
      }
    }

    const previous = Math.max(0, low - 1);
    return Math.abs(sortedPoints[previous].time - time) <= Math.abs(sortedPoints[low].time - time)
      ? sortedPoints[previous]
      : sortedPoints[low];
  };
}

export default function EquityChart({
  language,
  points,
  showTradeMarkers = false,
  themeMode,
  trades = [],
}: EquityChartProps) {
  const lineData = useMemo(() => toLineData(points), [points]);
  const tradeMarkers = useMemo(
    () => createTradeMarkers(trades, language),
    [language, trades],
  );
  const containerRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const lineSeriesRef = useRef<ISeriesApi<'Line'> | null>(null);
  const markersRef = useRef<ISeriesMarkersPluginApi<Time> | null>(null);
  const lineDataRef = useRef(lineData);
  const tradeMarkersRef = useRef(tradeMarkers);
  const showTradeMarkersRef = useRef(showTradeMarkers);
  const pointMapRef = useRef(createEquityPointMap(points));
  const nearestPointRef = useRef(createNearestPointLookup(points));
  const [activePoint, setActivePoint] = useState<ActiveEquityPoint | null>(null);

  useEffect(() => {
    pointMapRef.current = createEquityPointMap(points);
    nearestPointRef.current = createNearestPointLookup(points);
  }, [points]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return undefined;

    const colors = CHART_THEME[themeMode];
    const chart = createChart(container, {
      autoSize: true,
      layout: {
        background: { type: ColorType.Solid, color: colors.background },
        textColor: colors.text,
        fontFamily: 'Inter, ui-sans-serif, system-ui, sans-serif',
      },
      localization: {
        locale: language,
        priceFormatter: (price: number) => formatMoney(price, language),
        timeFormatter: (time: Time) => formatChartTime(Number(time), language),
      },
      grid: {
        vertLines: { color: colors.grid },
        horzLines: { color: colors.grid },
      },
      crosshair: {
        mode: CrosshairMode.Normal,
        vertLine: {
          color: colors.crosshair,
          labelBackgroundColor: colors.labelBackground,
        },
        horzLine: {
          color: colors.crosshair,
          labelBackgroundColor: colors.labelBackground,
        },
      },
      rightPriceScale: {
        borderColor: colors.border,
        scaleMargins: {
          top: CHART_PRICE_MARGIN_TOP,
          bottom: CHART_PRICE_MARGIN_BOTTOM,
        },
      },
      timeScale: {
        borderColor: colors.border,
        timeVisible: true,
        secondsVisible: false,
        rightOffset: CHART_RIGHT_OFFSET,
        barSpacing: CHART_BAR_SPACING,
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

    const lineSeries = chart.addSeries(LineSeries, {
      color: '#38bdf8',
      lineWidth: 3,
      priceLineVisible: true,
      lastValueVisible: true,
      title: 'Equity',
    });
    const markers = createSeriesMarkers(lineSeries, [], { zOrder: 'top' });
    lineSeries.setData(lineDataRef.current);
    markers.setMarkers(showTradeMarkersRef.current ? tradeMarkersRef.current : []);
    chart.timeScale().fitContent();

    const handleCrosshairMove = (param: MouseEventParams<Time>) => {
      if (!param.point || param.point.x < 0 || param.point.y < 0 || !param.time) {
        setActivePoint(null);
        return;
      }

      const time = Number(param.time);
      const point = pointMapRef.current.get(time) ?? nearestPointRef.current(time);
      setActivePoint(point ? { point, x: param.point.x, y: param.point.y } : null);
    };

    chart.subscribeCrosshairMove(handleCrosshairMove);
    chartRef.current = chart;
    lineSeriesRef.current = lineSeries;
    markersRef.current = markers;

    return () => {
      chart.unsubscribeCrosshairMove(handleCrosshairMove);
      markers.detach();
      chart.remove();
      chartRef.current = null;
      lineSeriesRef.current = null;
      markersRef.current = null;
    };
  }, [language, themeMode]);

  useEffect(() => {
    lineDataRef.current = lineData;
    lineSeriesRef.current?.setData(lineData);
    chartRef.current?.timeScale().fitContent();
  }, [lineData]);

  useEffect(() => {
    tradeMarkersRef.current = tradeMarkers;
    showTradeMarkersRef.current = showTradeMarkers;
    markersRef.current?.setMarkers(showTradeMarkers ? tradeMarkers : []);
  }, [showTradeMarkers, tradeMarkers]);

  if (!points.length) return <Empty description="No equity data" />;

  const chartWidth = containerRef.current?.clientWidth ?? 320;
  const chartHeight = containerRef.current?.clientHeight ?? 320;
  const tooltipLeft = activePoint
    ? Math.min(Math.max(activePoint.x + 14, 8), Math.max(8, chartWidth - 198))
    : 8;
  const tooltipTop = activePoint
    ? Math.min(Math.max(activePoint.y + 14, 8), Math.max(8, chartHeight - 148))
    : 8;

  return (
    <div className="equity-chart-shell">
      <div ref={containerRef} className="equity-chart" />
      <span className="equity-chart-axis-label equity-chart-axis-label--y">Equity</span>
      <span className="equity-chart-axis-label equity-chart-axis-label--x">Time</span>
      {activePoint ? (
        <div
          className="equity-tooltip-popover"
          role="status"
          style={{
            left: tooltipLeft,
            top: tooltipTop,
          }}
        >
          <div className="equity-tooltip__time">
            {formatChartTime(activePoint.point.time, language)}
          </div>
          <div className="equity-tooltip__grid">
            <span>Equity</span>
            <strong>{formatMoney(activePoint.point.equity, language)}</strong>
            <span>Cash</span>
            <strong>{formatMoney(activePoint.point.cash, language)}</strong>
            <span>Position</span>
            <strong>{activePoint.point.position.toLocaleString(language)}</strong>
          </div>
        </div>
      ) : null}
    </div>
  );
}
