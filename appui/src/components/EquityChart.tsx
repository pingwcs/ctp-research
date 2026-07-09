import Empty from 'antd/es/empty';
import { useMemo, useState, type MouseEvent } from 'react';

import type { BacktestTrade, EquityPoint } from '../api/backtest';
import { CHART_TIME_ZONE } from '../config/chart';
import {
  TRADE_MARKER_SIZE,
  TRADE_MARKER_STYLES,
  type TradeSide,
} from '../config/tradeMarkers';
import type { Language } from '../store/configSlice';
import { getEquityTooltipPlacement } from './equityTooltip';

const TIME_FORMAT_OPTIONS: Intl.DateTimeFormatOptions = {
  timeZone: CHART_TIME_ZONE,
  year: 'numeric',
  month: 'numeric',
  day: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
  second: '2-digit',
  hour12: false,
};

const MONEY_FORMAT_OPTIONS: Intl.NumberFormatOptions = {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
};

const EQUITY_CHART_WIDTH = 900;
const EQUITY_CHART_HEIGHT = 240;
const MAX_POINTS_PER_PIXEL = 2;

type EquityChartPoint = EquityPoint & {
  x: number;
  y: number;
};

type EquityTradePoint = EquityChartPoint & {
  className: string;
  color: string;
  label: string;
  shape: (typeof TRADE_MARKER_STYLES)[TradeSide]['shape'];
  trade: BacktestTrade;
};

function formatTime(value: number, formatter: Intl.DateTimeFormat) {
  return formatter.format(new Date(value * 1000));
}

function formatMoney(value: number, formatter: Intl.NumberFormat) {
  return formatter.format(value);
}

function getEquityDomain(points: EquityPoint[]) {
  let min = points[0].equity;
  let max = points[0].equity;

  for (let index = 1; index < points.length; index += 1) {
    const { equity } = points[index];
    if (equity < min) min = equity;
    if (equity > max) max = equity;
  }

  return { min, span: max - min || 1 };
}

function createChartPoint(
  point: EquityPoint,
  index: number,
  total: number,
  min: number,
  span: number,
): EquityChartPoint {
  const x = (index / Math.max(1, total - 1)) * EQUITY_CHART_WIDTH;
  const y = EQUITY_CHART_HEIGHT - ((point.equity - min) / span) * EQUITY_CHART_HEIGHT;
  return { ...point, x, y };
}

function createSampledChartPoints(points: EquityPoint[], min: number, span: number) {
  const total = points.length;
  const maxPoints = EQUITY_CHART_WIDTH * MAX_POINTS_PER_PIXEL;
  if (total <= maxPoints) {
    return points.map((point, index) => createChartPoint(point, index, total, min, span));
  }

  const sampled: EquityChartPoint[] = [];
  const lastIndex = total - 1;
  const bucketSize = total / EQUITY_CHART_WIDTH;

  const addPoint = (index: number) => {
    const previousPoint = sampled[sampled.length - 1];
    if (previousPoint?.time === points[index].time) return;
    sampled.push(createChartPoint(points[index], index, total, min, span));
  };

  addPoint(0);
  for (
    let bucketStart = 1;
    bucketStart < lastIndex;
    bucketStart = Math.ceil(bucketStart + bucketSize)
  ) {
    const bucketEnd = Math.min(lastIndex, Math.ceil(bucketStart + bucketSize));
    let minIndex = bucketStart;
    let maxIndex = bucketStart;

    for (let index = bucketStart + 1; index < bucketEnd; index += 1) {
      if (points[index].equity < points[minIndex].equity) minIndex = index;
      if (points[index].equity > points[maxIndex].equity) maxIndex = index;
    }

    if (minIndex < maxIndex) {
      addPoint(minIndex);
      addPoint(maxIndex);
    } else {
      addPoint(maxIndex);
      addPoint(minIndex);
    }
  }
  addPoint(lastIndex);

  return sampled;
}

function clamp(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value));
}

function findNearestEquityPointIndex(points: EquityPoint[], time: number) {
  let low = 0;
  let high = points.length - 1;

  while (low < high) {
    const middle = Math.floor((low + high) / 2);
    if (points[middle].time < time) {
      low = middle + 1;
    } else {
      high = middle;
    }
  }

  const previous = Math.max(0, low - 1);
  return Math.abs(points[previous].time - time) <= Math.abs(points[low].time - time)
    ? previous
    : low;
}

function createTradePoints(
  points: EquityPoint[],
  trades: BacktestTrade[],
  min: number,
  span: number,
): EquityTradePoint[] {
  return trades.map((trade) => {
    const pointIndex = findNearestEquityPointIndex(points, trade.time);
    const point = createChartPoint(points[pointIndex], pointIndex, points.length, min, span);
    const style = TRADE_MARKER_STYLES[trade.side];
    return {
      ...point,
      y: clamp(point.y, TRADE_MARKER_SIZE + 2, EQUITY_CHART_HEIGHT - TRADE_MARKER_SIZE - 2),
      className: style.className,
      color: style.color,
      label: style.label,
      shape: style.shape,
      trade,
    };
  });
}

function findNearestPointIndex(points: EquityChartPoint[], x: number) {
  let low = 0;
  let high = points.length - 1;

  while (low < high) {
    const middle = Math.floor((low + high) / 2);
    if (points[middle].x < x) {
      low = middle + 1;
    } else {
      high = middle;
    }
  }

  const previous = Math.max(0, low - 1);
  return Math.abs(points[previous].x - x) <= Math.abs(points[low].x - x) ? previous : low;
}

function tradePointPolygonPoints(marker: EquityTradePoint) {
  const size = TRADE_MARKER_SIZE;
  if (marker.shape === 'triangleUp') {
    return `${marker.x},${marker.y - size} ${marker.x - size},${marker.y + size} ${
      marker.x + size
    },${marker.y + size}`;
  }
  return `${marker.x},${marker.y + size} ${marker.x - size},${marker.y - size} ${
    marker.x + size
  },${marker.y - size}`;
}

export default function EquityChart({
  language,
  points,
  trades = [],
}: {
  language: Language;
  points: EquityPoint[];
  trades?: BacktestTrade[];
}) {
  const [activeIndex, setActiveIndex] = useState<number | null>(null);
  const timeFormatter = useMemo(
    () => new Intl.DateTimeFormat(language, TIME_FORMAT_OPTIONS),
    [language],
  );
  const moneyFormatter = useMemo(
    () => new Intl.NumberFormat(language, MONEY_FORMAT_OPTIONS),
    [language],
  );
  const chart = useMemo(() => {
    if (!points.length) {
      return {
        chartPoints: [] as EquityChartPoint[],
        polyline: '',
        tradePoints: [] as EquityTradePoint[],
      };
    }

    const { min, span } = getEquityDomain(points);
    const chartPoints = createSampledChartPoints(points, min, span);

    return {
      chartPoints,
      polyline: chartPoints.map((point) => `${point.x},${point.y}`).join(' '),
      tradePoints: createTradePoints(points, trades, min, span),
    };
  }, [points, trades]);

  if (!points.length) return <Empty description="No equity data" />;

  const activePoint = activeIndex === null ? null : (chart.chartPoints[activeIndex] ?? null);

  const updateActivePoint = (event: MouseEvent<HTMLDivElement>) => {
    if (chart.chartPoints.length <= 1) {
      setActiveIndex(0);
      return;
    }

    const rect = event.currentTarget.getBoundingClientRect();
    const ratio = Math.min(1, Math.max(0, (event.clientX - rect.left) / rect.width));
    setActiveIndex(findNearestPointIndex(chart.chartPoints, ratio * EQUITY_CHART_WIDTH));
  };

  return (
    <div
      className="equity-chart-shell"
      onMouseLeave={() => setActiveIndex(null)}
      onMouseMove={updateActivePoint}
    >
      <svg
        aria-label="Equity curve"
        className="equity-chart"
        preserveAspectRatio="none"
        role="img"
        viewBox={`0 0 ${EQUITY_CHART_WIDTH} ${EQUITY_CHART_HEIGHT}`}
      >
        <polyline
          fill="none"
          points={chart.polyline}
          stroke="#38bdf8"
          strokeLinecap="round"
          strokeWidth="3"
        />
        {chart.tradePoints.map((marker, index) => (
          <g
            className={`equity-trade-marker ${marker.className}`}
            key={`${marker.trade.time}-${marker.trade.side}-${index}`}
          >
            <title>
              {marker.label} {formatMoney(marker.trade.price, moneyFormatter)}
            </title>
            <polygon
              className="equity-trade-marker__shape"
              fill={marker.color}
              points={tradePointPolygonPoints(marker)}
            />
          </g>
        ))}
        {activePoint ? (
          <>
            <line
              className="equity-chart__guide"
              x1={activePoint.x}
              x2={activePoint.x}
              y1="0"
              y2={EQUITY_CHART_HEIGHT}
            />
            <circle className="equity-chart__point" cx={activePoint.x} cy={activePoint.y} r="5" />
          </>
        ) : null}
      </svg>
      {activePoint ? (
        <>
          <span
            aria-hidden
            className="equity-chart__active-anchor"
            style={{
              left: `${(activePoint.x / EQUITY_CHART_WIDTH) * 100}%`,
              top: `${(activePoint.y / EQUITY_CHART_HEIGHT) * 100}%`,
            }}
          />
          <div
            className="equity-tooltip-popover"
            role="status"
            style={getEquityTooltipPlacement(activePoint, {
              height: EQUITY_CHART_HEIGHT,
              width: EQUITY_CHART_WIDTH,
            })}
          >
            <div className="equity-tooltip__time">
              {formatTime(activePoint.time, timeFormatter)}
            </div>
            <div className="equity-tooltip__grid">
              <span>Equity</span>
              <strong>{formatMoney(activePoint.equity, moneyFormatter)}</strong>
              <span>Cash</span>
              <strong>{formatMoney(activePoint.cash, moneyFormatter)}</strong>
              <span>Position</span>
              <strong>{activePoint.position.toLocaleString(language)}</strong>
            </div>
          </div>
        </>
      ) : null}
    </div>
  );
}
