import Empty from 'antd/es/empty';
import Tooltip from 'antd/es/tooltip';
import { useMemo, useState, type MouseEvent } from 'react';

import type { EquityPoint } from '../api/backtest';
import { CHART_TIME_ZONE } from '../config/chart';
import type { Language } from '../store/configSlice';

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

export default function EquityChart({
  language,
  points,
}: {
  language: Language;
  points: EquityPoint[];
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
      };
    }

    const { min, span } = getEquityDomain(points);
    const chartPoints = createSampledChartPoints(points, min, span);

    return {
      chartPoints,
      polyline: chartPoints.map((point) => `${point.x},${point.y}`).join(' '),
    };
  }, [points]);

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
        <Tooltip
          destroyOnHidden
          open
          placement="top"
          title={
            <div className="equity-tooltip">
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
          }
        >
          <span
            className="equity-chart__active-anchor"
            style={{
              left: `${(activePoint.x / EQUITY_CHART_WIDTH) * 100}%`,
              top: `${(activePoint.y / EQUITY_CHART_HEIGHT) * 100}%`,
            }}
          />
        </Tooltip>
      ) : null}
    </div>
  );
}
