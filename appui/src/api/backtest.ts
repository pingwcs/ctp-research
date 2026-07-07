import { API_ROUTES } from '../config/api';
import { http } from './http';

export interface StrategyInfo {
  id: string;
  name: string;
  description: string;
}

export interface MetricInfo {
  id: string;
  name: string;
  description: string;
}

export interface BacktestTrade {
  time: number;
  side: 'buy' | 'sell';
  price: number;
  quantity: number;
  cash: number;
  reason: string;
}

export interface EquityPoint {
  time: number;
  equity: number;
  cash: number;
  position_value: number;
  position: number;
}

export interface BacktestResult {
  symbol: string;
  strategy: string;
  initial_cash: number;
  final_equity: number;
  trades: BacktestTrade[];
  equity_curve: EquityPoint[];
  metrics: Record<string, number | null>;
}

export interface BacktestRunParams {
  symbol: string;
  strategy: string;
  start_time?: string | null;
  end_time?: string | null;
  metrics: string[];
}

export function fetchBacktestStrategies() {
  return http.get<StrategyInfo[]>(API_ROUTES.backtestStrategies);
}

export function fetchBacktestSymbols() {
  return http.get<string[]>(API_ROUTES.backtestSymbols);
}

export function fetchBacktestMetrics() {
  return http.get<MetricInfo[]>(API_ROUTES.backtestMetrics);
}

export function runBacktestRequest(params: BacktestRunParams) {
  return http.post<BacktestResult, BacktestRunParams>(API_ROUTES.backtestRun, params);
}
