import { API_ROUTES } from '.';
import { http } from './http';

export type TradeSignalText = 'Buy' | 'Sell';

export interface Candle {
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface TradeMarker {
  time: number;
  position: 'aboveBar' | 'belowBar';
  color: string;
  shape: 'arrowUp' | 'arrowDown';
  text: TradeSignalText;
}

export interface KLineResponse {
  symbol: string;
  total: number;
  offset: number;
  limit: number;
  candles: Candle[];
  markers: TradeMarker[];
}

export interface KLineRequest {
  symbol: string;
  offset?: number;
  limit?: number;
}

export function fetchKLine(params: KLineRequest) {
  return http.get<KLineResponse>(API_ROUTES.marketKline, { params });
}
