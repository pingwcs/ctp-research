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

type TooltipValueKey = 'open' | 'high' | 'low' | 'close' | 'volume';

interface TooltipView {
  time: HTMLDivElement;
  values: Record<TooltipValueKey, HTMLElement>;
  pendingPosition: {
    point: Point;
    container: HTMLDivElement;
  } | null;
  rafId: number | null;
}

const tooltipViews = new WeakMap<HTMLDivElement, TooltipView>();
const valueRows: Array<[label: string, key: TooltipValueKey]> = [
  ['Open', 'open'],
  ['High', 'high'],
  ['Low', 'low'],
  ['Close', 'close'],
  ['Vol', 'volume'],
];

function ensureTooltipView(tooltip: HTMLDivElement) {
  const existingView = tooltipViews.get(tooltip);
  if (existingView) return existingView;

  const time = document.createElement('div');
  time.className = 'chart-tooltip__time';

  const grid = document.createElement('div');
  grid.className = 'chart-tooltip__grid';

  const values = {} as Record<TooltipValueKey, HTMLElement>;
  valueRows.forEach(([label, key]) => {
    const labelNode = document.createElement('span');
    const valueNode = document.createElement('strong');

    labelNode.textContent = label;
    grid.append(labelNode, valueNode);
    values[key] = valueNode;
  });

  tooltip.replaceChildren(time, grid);

  const view: TooltipView = {
    time,
    values,
    pendingPosition: null,
    rafId: null,
  };
  tooltipViews.set(tooltip, view);
  return view;
}

function scheduleTooltipPosition(
  tooltip: HTMLDivElement,
  view: TooltipView,
  point: Point,
  container: HTMLDivElement,
) {
  view.pendingPosition = { point, container };
  if (view.rafId !== null) return;

  view.rafId = requestAnimationFrame(() => {
    view.rafId = null;
    const pending = view.pendingPosition;
    if (!pending) return;

    const { clientHeight: height, clientWidth: width } = pending.container;
    const maxLeft = Math.max(TOOLTIP_PAD, width - TOOLTIP_MIN_WIDTH - TOOLTIP_PAD);
    const maxTop = Math.max(TOOLTIP_PAD, height - TOOLTIP_MIN_HEIGHT - TOOLTIP_PAD);
    const left = Math.min(Math.max(pending.point.x + TOOLTIP_OFFSET, TOOLTIP_PAD), maxLeft);
    const top = Math.min(Math.max(pending.point.y + TOOLTIP_OFFSET, TOOLTIP_PAD), maxTop);

    tooltip.style.transform = `translate(${left}px, ${top}px)`;
    tooltip.style.opacity = '1';
  });
}

export function hideKLineTooltip(tooltip: HTMLDivElement | null) {
  if (!tooltip) return;

  const view = tooltipViews.get(tooltip);
  if (view?.rafId !== null && view?.rafId !== undefined) {
    cancelAnimationFrame(view.rafId);
    view.rafId = null;
  }
  if (view) {
    view.pendingPosition = null;
  }
  tooltip.style.opacity = '0';
}

export function renderKLineTooltip(
  tooltip: HTMLDivElement | null,
  candle: Candle | undefined,
  point: Point | null,
  container: HTMLDivElement | null,
  language: Language,
) {
  if (!tooltip || !candle || !point || !container) return;

  const view = ensureTooltipView(tooltip);
  const isUp = candle.close >= candle.open;

  tooltip.classList.add('chart-tooltip');
  tooltip.classList.toggle('is-up', isUp);
  tooltip.classList.toggle('is-down', !isUp);

  view.time.textContent = formatChartTime(candle.time, language);
  view.values.open.textContent = formatChartNumber(candle.open, language);
  view.values.high.textContent = formatChartNumber(candle.high, language);
  view.values.low.textContent = formatChartNumber(candle.low, language);
  view.values.close.textContent = formatChartNumber(candle.close, language);
  view.values.volume.textContent = formatChartVolume(candle.volume, language);

  scheduleTooltipPosition(tooltip, view, point, container);
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
