import { API_ROUTES } from '.';
import { http } from './http';
import type {
  BacktestTrade,
  BacktestRunRequest,
  BacktestRunResponse,
  EquityPoint,
  MetricInfo,
  StrategyInfo,
} from './generated/types';

export type {
  BacktestRunRequest as BacktestRunParams,
  BacktestRunResponse as BacktestResult,
  BacktestTrade,
  EquityPoint,
  MetricInfo,
  StrategyInfo,
};

export function fetchBacktestStrategies() {
  return http.get<StrategyInfo[]>(API_ROUTES.backtestStrategies);
}

export function fetchBacktestSymbols() {
  return http.get<string[]>(API_ROUTES.backtestSymbols);
}

export function fetchBacktestMetrics() {
  return http.get<MetricInfo[]>(API_ROUTES.backtestMetrics);
}

export function runBacktestRequest(params: BacktestRunRequest) {
  return http.post<BacktestRunResponse, BacktestRunRequest>(API_ROUTES.backtestRun, params);
}
