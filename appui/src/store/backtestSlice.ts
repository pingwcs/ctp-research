import { createAsyncThunk, createSlice, type PayloadAction } from '@reduxjs/toolkit';

import {
  fetchBacktestMetrics,
  fetchBacktestStrategies,
  fetchBacktestSymbols,
  runBacktestRequest,
  type BacktestResult,
  type BacktestRunParams,
  type MetricInfo,
  type StrategyInfo,
} from '../api/backtest';

interface BacktestState {
  strategies: StrategyInfo[];
  symbols: string[];
  metrics: MetricInfo[];
  selectedStrategy: string;
  selectedSymbol: string;
  selectedMetrics: string[];
  startTime: string;
  endTime: string;
  result: BacktestResult | null;
  loadingOptions: boolean;
  running: boolean;
  error: string | null;
}

const DEFAULT_METRIC_COUNT = 3;

interface BacktestOptionsPayload {
  strategies: StrategyInfo[];
  symbols: string[];
  metrics: MetricInfo[];
}

const initialState: BacktestState = {
  strategies: [],
  symbols: [],
  metrics: [],
  selectedStrategy: 'ma_cross',
  selectedSymbol: '',
  selectedMetrics: ['total_return', 'sharpe', 'max_drawdown'],
  startTime: '',
  endTime: '',
  result: null,
  loadingOptions: false,
  running: false,
  error: null,
};

function getErrorMessage(error: unknown, fallback: string) {
  return error instanceof Error && error.message ? error.message : fallback;
}

export const fetchBacktestOptions = createAsyncThunk<
  BacktestOptionsPayload,
  void,
  { rejectValue: string }
>('backtest/fetchOptions', async (_, { rejectWithValue }) => {
  try {
    const [strategies, symbols, metrics] = await Promise.all([
      fetchBacktestStrategies(),
      fetchBacktestSymbols(),
      fetchBacktestMetrics(),
    ]);
    return { strategies, symbols, metrics };
  } catch (error) {
    return rejectWithValue(getErrorMessage(error, 'Failed to load backtest options'));
  }
});

export const runBacktest = createAsyncThunk<
  BacktestResult,
  BacktestRunParams,
  { rejectValue: string }
>('backtest/run', async (params, { rejectWithValue }) => {
  try {
    return await runBacktestRequest(params);
  } catch (error) {
    return rejectWithValue(getErrorMessage(error, 'Backtest failed'));
  }
});

const backtestSlice = createSlice({
  name: 'backtest',
  initialState,
  reducers: {
    setSelectedStrategy(state, action: PayloadAction<string>) {
      state.selectedStrategy = action.payload;
    },
    setSelectedSymbol(state, action: PayloadAction<string>) {
      state.selectedSymbol = action.payload;
    },
    setSelectedMetrics(state, action: PayloadAction<string[]>) {
      state.selectedMetrics = action.payload;
    },
    setStartTime(state, action: PayloadAction<string>) {
      state.startTime = action.payload;
    },
    setEndTime(state, action: PayloadAction<string>) {
      state.endTime = action.payload;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchBacktestOptions.pending, (state) => {
        state.loadingOptions = true;
        state.error = null;
      })
      .addCase(fetchBacktestOptions.fulfilled, (state, action) => {
        state.loadingOptions = false;
        state.strategies = action.payload.strategies;
        state.symbols = action.payload.symbols;
        state.metrics = action.payload.metrics;
        if (!state.selectedSymbol && action.payload.symbols.length) {
          state.selectedSymbol = action.payload.symbols[0];
        }
        if (!state.selectedMetrics.length) {
          state.selectedMetrics = action.payload.metrics
            .slice(0, DEFAULT_METRIC_COUNT)
            .map((metric) => metric.id);
        }
      })
      .addCase(fetchBacktestOptions.rejected, (state, action) => {
        state.loadingOptions = false;
        state.error = action.payload || action.error.message || 'Failed to load backtest options';
      })
      .addCase(runBacktest.pending, (state) => {
        state.running = true;
        state.error = null;
      })
      .addCase(runBacktest.fulfilled, (state, action) => {
        state.running = false;
        state.result = action.payload;
      })
      .addCase(runBacktest.rejected, (state, action) => {
        state.running = false;
        state.error = action.payload || action.error.message || 'Backtest failed';
      });
  },
});

export const {
  setSelectedStrategy,
  setSelectedSymbol,
  setSelectedMetrics,
  setStartTime,
  setEndTime,
} = backtestSlice.actions;
export default backtestSlice.reducer;
