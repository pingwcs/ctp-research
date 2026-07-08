import { createAsyncThunk, createSlice, type PayloadAction } from '@reduxjs/toolkit';

import {
  fetchKLine,
  type Candle,
  type KLineRequest,
  type KLineResponse,
  type TradeMarker,
} from '../api/market';
import { DEFAULT_KLINE_LIMIT, DEFAULT_SYMBOL } from '../config/chart';

interface MarketState {
  symbol: string;
  candles: Candle[];
  markers: TradeMarker[];
  total: number;
  // First global bar index in candles; the chart uses it to keep a stable
  // visible range while background preloading swaps the loaded data window.
  offset: number;
  limit: number;
  loading: boolean;
  error: string | null;
  lastLoadedTime: number | null;
  // Offset:limit key for suppressing duplicate range requests from chart drags.
  lastRequestedRange: string | null;
  activeRequestId: string | null;
  activeRequestKey: string | null;
}

const initialState: MarketState = {
  symbol: DEFAULT_SYMBOL,
  candles: [],
  markers: [],
  total: 0,
  offset: 0,
  limit: DEFAULT_KLINE_LIMIT,
  loading: false,
  error: null,
  lastLoadedTime: null,
  lastRequestedRange: null,
  activeRequestId: null,
  activeRequestKey: null,
};

export const fetchKLineData = createAsyncThunk<
  KLineResponse,
  KLineRequest,
  { rejectValue: string }
>('market/fetchKLineData', async (request, { rejectWithValue, signal }) => {
  try {
    return await fetchKLine(request, signal);
  } catch (error) {
    if (signal.aborted) {
      return rejectWithValue('Request canceled');
    }

    const message = error instanceof Error ? error.message : '网络异常，无法连接行情 API';
    return rejectWithValue(message);
  }
});

function getKLineRequestKey(request: KLineRequest) {
  const symbol = request.symbol.trim().toUpperCase();
  const offset = request.offset ?? 0;
  const limit = request.limit ?? DEFAULT_KLINE_LIMIT;
  return `${symbol}:${offset}:${limit}`;
}

function isActiveRequest(state: MarketState, requestId: string, request: KLineRequest) {
  return (
    state.activeRequestId === requestId && state.activeRequestKey === getKLineRequestKey(request)
  );
}

const marketSlice = createSlice({
  name: 'market',
  initialState,
  reducers: {
    setSymbol(state, action: PayloadAction<string>) {
      state.symbol = action.payload.trim().toUpperCase();
      state.lastRequestedRange = null;
    },
    clearError(state) {
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchKLineData.pending, (state, action) => {
        state.loading = true;
        state.error = null;
        state.activeRequestId = action.meta.requestId;
        state.activeRequestKey = getKLineRequestKey(action.meta.arg);
      })
      .addCase(fetchKLineData.fulfilled, (state, action) => {
        if (!isActiveRequest(state, action.meta.requestId, action.meta.arg)) return;

        state.loading = false;
        state.symbol = action.payload.symbol;
        state.candles = action.payload.candles;
        state.markers = action.payload.markers;
        state.total = action.payload.total;
        state.offset = action.payload.offset;
        state.limit = action.payload.limit;
        state.lastRequestedRange = `${action.payload.offset}:${action.payload.limit}`;
        state.lastLoadedTime = Date.now();
        state.activeRequestId = null;
        state.activeRequestKey = null;
      })
      .addCase(fetchKLineData.rejected, (state, action) => {
        if (!isActiveRequest(state, action.meta.requestId, action.meta.arg)) return;

        state.loading = false;
        state.activeRequestId = null;
        state.activeRequestKey = null;
        if (!action.meta.aborted) {
          state.error = action.payload || action.error.message || '行情数据加载失败';
        }
      });
  },
});

export const { setSymbol, clearError } = marketSlice.actions;
export default marketSlice.reducer;
