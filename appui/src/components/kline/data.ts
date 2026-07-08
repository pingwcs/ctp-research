import {
  type CandlestickData,
  type HistogramData,
  type SeriesMarker,
  type Time,
  type UTCTimestamp,
} from 'lightweight-charts';

import type { Candle, TradeMarker } from '../../api/market';
import { CHART_TIME_ZONE, NUMBER_FORMAT_OPTIONS, VOLUME_FORMAT_OPTIONS } from '../../config/chart';
import { CHART_PALETTE } from '../../config/theme';
import type { CandleColorScheme, Language } from '../../store/configSlice';

const numberFormatters = new Map<Language, Intl.NumberFormat>();
const volumeFormatters = new Map<Language, Intl.NumberFormat>();

function getFormatter(
  cache: Map<Language, Intl.NumberFormat>,
  language: Language,
  options: Intl.NumberFormatOptions,
) {
  const cachedFormatter = cache.get(language);
  if (cachedFormatter) return cachedFormatter;

  const formatter = new Intl.NumberFormat(language, options);
  cache.set(language, formatter);
  return formatter;
}

export function formatChartNumber(value: number, language: Language) {
  return getFormatter(numberFormatters, language, NUMBER_FORMAT_OPTIONS).format(value);
}

export function formatChartVolume(value: number, language: Language) {
  return getFormatter(volumeFormatters, language, VOLUME_FORMAT_OPTIONS).format(value);
}

function toUtcTimestamp(time: number): UTCTimestamp {
  return time as UTCTimestamp;
}

export function formatChartTime(time: number, language: Language) {
  return new Date(time * 1000).toLocaleString(language, {
    hour12: false,
    timeZone: CHART_TIME_ZONE,
  });
}

export function toCandleData(candles: Candle[]): CandlestickData<UTCTimestamp>[] {
  return candles.map((item) => ({
    time: toUtcTimestamp(item.time),
    open: item.open,
    high: item.high,
    low: item.low,
    close: item.close,
  }));
}

export function toVolumeData(
  candles: Candle[],
  colorScheme: CandleColorScheme,
): HistogramData<UTCTimestamp>[] {
  const colors = CHART_PALETTE[colorScheme];
  return candles.map((item) => ({
    time: toUtcTimestamp(item.time),
    value: item.volume,
    color: item.close >= item.open ? colors.upVolume : colors.downVolume,
  }));
}

export function toMaData(candles: Candle[], windowSize: number) {
  // Use the available leading bars before a full window exists so the MA
  // overlay starts at the first candle instead of appearing later.
  let rollingSum = 0;

  return candles.map((item, index) => {
    rollingSum += item.close;
    if (index >= windowSize) {
      rollingSum -= candles[index - windowSize].close;
    }

    const sampleSize = Math.min(index + 1, windowSize);
    return {
      time: toUtcTimestamp(item.time),
      value: rollingSum / sampleSize,
    };
  });
}

export function toSeriesMarkers(markers: TradeMarker[]): SeriesMarker<Time>[] {
  return markers.map((item) => ({
    time: toUtcTimestamp(item.time),
    position: item.position,
    color: item.color,
    shape: item.shape,
    text: item.text,
  }));
}
