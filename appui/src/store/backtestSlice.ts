import { createAction, createAsyncThunk, createSlice, type PayloadAction } from '@reduxjs/toolkit';

import {
  fetchBacktestJobResult,
  fetchBacktestJobStatus,
  fetchBacktestMetrics,
  fetchBacktestStrategies,
  fetchBacktestSymbols,
  submitBacktestJob,
  type BacktestJobStatus,
  type BacktestJobSubmission,
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
  activeJobId: string;
  jobStatus: BacktestJobStatus['status'] | '';
  loadingOptions: boolean;
  running: boolean;
  error: string | null;
}

const DEFAULT_METRIC_COUNT = 3;
const JOB_POLL_INTERVAL_MS = 750;
const MAX_JOB_POLLS = 240;

interface BacktestOptionsPayload {
  strategies: StrategyInfo[];
  symbols: string[];
  metrics: MetricInfo[];
}

const initialState: BacktestState = {
  strategies: [],
  symbols: [],
  metrics: [],
  selectedStrategy: '',
  selectedSymbol: '',
  selectedMetrics: [],
  startTime: '',
  endTime: '',
  result: null,
  activeJobId: '',
  jobStatus: '',
  loadingOptions: false,
  running: false,
  error: null,
};

function getErrorMessage(error: unknown, fallback: string) {
  return error instanceof Error && error.message ? error.message : fallback;
}

const wait = (ms: number) => new Promise((resolve) => window.setTimeout(resolve, ms));

const backtestJobSubmitted = createAction<BacktestJobSubmission>('backtest/jobSubmitted');
const backtestJobStatusReceived = createAction<BacktestJobStatus>('backtest/jobStatusReceived');

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
>('backtest/run', async (params, { dispatch, rejectWithValue }) => {
  try {
    const submitted = await submitBacktestJob(params);
    dispatch(backtestJobSubmitted(submitted));

    let current: BacktestJobStatus = {
      job_id: submitted.job_id,
      status: submitted.status,
      error: null,
    };
    for (let attempt = 0; attempt < MAX_JOB_POLLS; attempt += 1) {
      if (current.status === 'succeeded') {
        return await fetchBacktestJobResult(submitted.job_id);
      }
      if (current.status === 'failed') {
        throw new Error(current.error || 'Backtest failed');
      }

      await wait(JOB_POLL_INTERVAL_MS);
      current = await fetchBacktestJobStatus(submitted.job_id);
      dispatch(backtestJobStatusReceived(current));
    }

    throw new Error('Backtest job timed out');
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
        if (
          action.payload.strategies.length &&
          !action.payload.strategies.some((strategy) => strategy.id === state.selectedStrategy)
        ) {
          state.selectedStrategy = action.payload.strategies[0].id;
        }
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
        state.activeJobId = '';
        state.jobStatus = '';
      })
      .addCase(backtestJobSubmitted, (state, action) => {
        state.activeJobId = action.payload.job_id;
        state.jobStatus = action.payload.status;
      })
      .addCase(backtestJobStatusReceived, (state, action) => {
        state.activeJobId = action.payload.job_id;
        state.jobStatus = action.payload.status;
      })
      .addCase(runBacktest.fulfilled, (state, action) => {
        state.running = false;
        state.jobStatus = 'succeeded';
        state.result = action.payload;
      })
      .addCase(runBacktest.rejected, (state, action) => {
        state.running = false;
        if (!state.jobStatus || state.jobStatus === 'running') {
          state.jobStatus = 'failed';
        }
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
