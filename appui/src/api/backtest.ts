import { API_ROUTES } from '.';
import { http } from './http';
import type {
  BacktestJobStatusResponse,
  BacktestJobSubmitResponse,
  BacktestTrade,
  BacktestRunRequest,
  BacktestRunResponse,
  EquityPoint,
  MetricInfo,
  StrategyInfo,
} from './generated/types';

export type {
  BacktestJobStatusResponse as BacktestJobStatus,
  BacktestJobSubmitResponse as BacktestJobSubmission,
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

export function submitBacktestJob(params: BacktestRunRequest) {
  return http.post<BacktestJobSubmitResponse, BacktestRunRequest>(API_ROUTES.backtestJobs, params);
}

export function fetchBacktestJobStatus(jobId: string) {
  return http.get<BacktestJobStatusResponse>(
    `${API_ROUTES.backtestJobs}/${encodeURIComponent(jobId)}`,
  );
}

export function fetchBacktestJobResult(jobId: string) {
  return http.get<BacktestRunResponse>(
    `${API_ROUTES.backtestJobs}/${encodeURIComponent(jobId)}/result`,
  );
}
