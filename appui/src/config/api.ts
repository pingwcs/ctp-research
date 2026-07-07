export const API_TIMEOUT_MS = 15000;

export const API_ROUTES = {
  marketKline: '/api/market/kline',
  backtestStrategies: '/api/backtest/strategies',
  backtestSymbols: '/api/backtest/symbols',
  backtestMetrics: '/api/backtest/metrics',
  backtestRun: '/api/backtest/run',
} as const;
