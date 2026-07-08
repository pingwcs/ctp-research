export const DEFAULT_SYMBOL = 'RB0909';
export const DEFAULT_KLINE_LIMIT = 2000;
export const MAX_WINDOW = DEFAULT_KLINE_LIMIT;



export const MA_WINDOW_MIN = 1;
export const MA_WINDOW_MAX = 200;

export const PRELOAD_BARS = 1000;

export const CHART_RANGE_THROTTLE_MS = 250;

export const MIN_BAR_SPACING = 1;
export const MAX_BAR_SPACING = 30;
export const CHART_RIGHT_OFFSET = 4;
export const CHART_BAR_SPACING = 6;
export const CHART_PRICE_MARGIN_TOP = 0.08;
export const CHART_PRICE_MARGIN_BOTTOM = 0.24;

export const TOOLTIP_MIN_WIDTH = 190;
export const TOOLTIP_MIN_HEIGHT = 132;
export const TOOLTIP_OFFSET = 16;
export const TOOLTIP_PAD = 8;

export const MA_COLORS = ['#38bdf8', '#facc15', '#c084fc'] as const;

export const NUMBER_FORMAT_OPTIONS: Intl.NumberFormatOptions = {
  maximumFractionDigits: 4,
};

export const VOLUME_FORMAT_OPTIONS: Intl.NumberFormatOptions = {
  maximumFractionDigits: 0,
};

export const CHART_TIME_ZONE = 'Asia/Shanghai';
