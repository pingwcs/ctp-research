import { type MouseEventParams, type Time } from 'lightweight-charts';

import type { Candle } from '../../api/market';
import {
  TOOLTIP_MIN_HEIGHT,
  TOOLTIP_MIN_WIDTH,
  TOOLTIP_OFFSET,
  TOOLTIP_PAD,
} from '../../config/chart';
import type { Language } from '../../store/configSlice';
import { formatChartNumber, formatChartTime, formatChartVolume } from './data';

interface Point {
  x: number;
  y: number;
}

interface RefBox<T> {
  current: T;
}

export function hideKLineTooltip(tooltip: HTMLDivElement | null) {
  if (tooltip) {
    tooltip.style.opacity = '0';
  }
}

export function renderKLineTooltip(
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
    <div class="chart-tooltip__time">${formatChartTime(candle.time, language)}</div>
    <div class="chart-tooltip__grid">
      <span>Open</span><strong>${formatChartNumber(candle.open, language)}</strong>
      <span>High</span><strong>${formatChartNumber(candle.high, language)}</strong>
      <span>Low</span><strong>${formatChartNumber(candle.low, language)}</strong>
      <span>Close</span><strong>${formatChartNumber(candle.close, language)}</strong>
      <span>Vol</span><strong>${formatChartVolume(candle.volume, language)}</strong>
    </div>
  `;

  const { width, height } = container.getBoundingClientRect();
  const tooltipWidth = tooltip.offsetWidth || TOOLTIP_MIN_WIDTH;
  const tooltipHeight = tooltip.offsetHeight || TOOLTIP_MIN_HEIGHT;
  const left = Math.min(
    Math.max(point.x + TOOLTIP_OFFSET, TOOLTIP_PAD),
    width - tooltipWidth - TOOLTIP_PAD,
  );
  const top = Math.min(
    Math.max(point.y + TOOLTIP_OFFSET, TOOLTIP_PAD),
    height - tooltipHeight - TOOLTIP_PAD,
  );

  tooltip.style.transform = `translate(${left}px, ${top}px)`;
  tooltip.style.opacity = '1';
}

export function createKLineCrosshairHandler(
  tooltipRef: RefBox<HTMLDivElement | null>,
  candleMapRef: RefBox<Map<number, Candle>>,
  containerRef: RefBox<HTMLDivElement | null>,
  languageRef: RefBox<Language>,
) {
  return (param: MouseEventParams<Time>) => {
    if (!param.point || !param.time || param.point.x < 0 || param.point.y < 0) {
      hideKLineTooltip(tooltipRef.current);
      return;
    }

    const candle = candleMapRef.current.get(Number(param.time));
    if (!candle) {
      hideKLineTooltip(tooltipRef.current);
      return;
    }

    renderKLineTooltip(
      tooltipRef.current,
      candle,
      param.point,
      containerRef.current,
      languageRef.current,
    );
  };
}
