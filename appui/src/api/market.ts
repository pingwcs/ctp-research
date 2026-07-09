import { API_ROUTES } from '.';
import { http } from './http';
import type { Candle, KLineResponse } from './generated/types';

export type { Candle, KLineResponse };

export interface KLineRequest {
  symbol: string;
  offset?: number;
  limit?: number;
}

export function fetchKLine(params: KLineRequest, signal?: AbortSignal) {
  return http.get<KLineResponse>(API_ROUTES.marketKline, { params, signal });
}
