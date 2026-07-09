import { useCallback, useEffect, useRef, type MutableRefObject } from 'react';
import {
  ColorType,
  CrosshairMode,
  PriceScaleMode,
  createChart,
  type IChartApi,
  type Time,
} from 'lightweight-charts';

import type { Candle } from '../../api/market';
import {
  CHART_BAR_SPACING,
  CHART_PRICE_MARGIN_BOTTOM,
  CHART_PRICE_MARGIN_TOP,
  CHART_RIGHT_OFFSET,
  MAX_BAR_SPACING,
  MIN_BAR_SPACING,
} from '../../config/chart';
import { CHART_THEME, type ThemeMode } from '../../config/theme';
import type { Language, PriceScale } from '../../store/configSlice';
import { formatChartNumber, formatChartTime } from './data';
import { createKLineCrosshairHandler, hideKLineTooltip } from './tooltip';
import type { LogicalRangeLike } from '../../hooks/useKLineRangePreload';

interface UseLightweightChartParams {
  candleMapRef: MutableRefObject<Map<number, Candle>>;
  containerRef: MutableRefObject<HTMLDivElement | null>;
  language: Language;
  onVisibleRangeChange: (range: LogicalRangeLike | null) => void;
  priceScale: PriceScale;
  themeMode: ThemeMode;
  tooltipRef: MutableRefObject<HTMLDivElement | null>;
}

function createBaseChart(
  container: HTMLDivElement,
  language: Language,
  priceScale: PriceScale,
  themeMode: ThemeMode,
) {
  const colors = CHART_THEME[themeMode];

  return createChart(container, {
    autoSize: true,
    layout: {
      background: { type: ColorType.Solid, color: colors.background },
      textColor: colors.text,
      fontFamily: 'Inter, ui-sans-serif, system-ui, sans-serif',
    },
    localization: {
      locale: language,
      priceFormatter: (price: number) => formatChartNumber(price, language),
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
      mode: priceScale === 'logarithmic' ? PriceScaleMode.Logarithmic : PriceScaleMode.Normal,
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

export function useLightweightChart({
  candleMapRef,
  containerRef,
  language,
  onVisibleRangeChange,
  priceScale,
  themeMode,
  tooltipRef,
}: UseLightweightChartParams) {
  const chartRef = useRef<IChartApi | null>(null);
  const initialOptionsRef = useRef({ language, priceScale, themeMode });
  const languageRef = useRef(language);

  languageRef.current = language;

  useEffect(() => {
    if (!containerRef.current) return undefined;

    const tooltip = tooltipRef.current;
    const chart = createBaseChart(
      containerRef.current,
      initialOptionsRef.current.language,
      initialOptionsRef.current.priceScale,
      initialOptionsRef.current.themeMode,
    );
    const onCrosshairMove = createKLineCrosshairHandler(
      tooltipRef,
      candleMapRef,
      containerRef,
      languageRef,
    );

    chart.subscribeCrosshairMove(onCrosshairMove);
    chart.timeScale().subscribeVisibleLogicalRangeChange(onVisibleRangeChange);
    chartRef.current = chart;

    return () => {
      hideKLineTooltip(tooltip);
      chart.unsubscribeCrosshairMove(onCrosshairMove);
      chart.timeScale().unsubscribeVisibleLogicalRangeChange(onVisibleRangeChange);
      chart.remove();
      chartRef.current = null;
    };
  }, [candleMapRef, containerRef, onVisibleRangeChange, tooltipRef]);

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
    const colors = CHART_THEME[themeMode];
    chartRef.current?.applyOptions({
      layout: {
        background: { type: ColorType.Solid, color: colors.background },
        textColor: colors.text,
      },
      grid: {
        vertLines: { color: colors.grid },
        horzLines: { color: colors.grid },
      },
      crosshair: {
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
      },
      timeScale: {
        borderColor: colors.border,
      },
    });
  }, [themeMode]);

  const resetTimeScale = useCallback(() => {
    chartRef.current?.timeScale().resetTimeScale();
  }, []);

  return {
    chartRef,
    resetTimeScale,
  };
}
