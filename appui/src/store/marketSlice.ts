import { createAsyncThunk, createSlice, type PayloadAction } from '@reduxjs/toolkit';

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
  candles: Candle[];
  markers: TradeMarker[];
}

interface MarketState {
  symbol: string;
  candles: Candle[];
  markers: TradeMarker[];
  loading: boolean;
  error: string | null;
  lastLoadedAt: number | null;
}

const initialState: MarketState = {
  symbol: 'RB0909',
  candles: [],
  markers: [],
  loading: false,
  error: null,
  lastLoadedAt: null,
};

export const fetchKLineData = createAsyncThunk<KLineResponse, string, { rejectValue: string }>(
  'market/fetchKLineData',
  async (symbol, { rejectWithValue }) => {
    try {
      const response = await fetch(`/api/market/kline?symbol=${encodeURIComponent(symbol)}`);
      const payload = (await response.json()) as KLineResponse | { detail?: string };
      if (!response.ok) {
        return rejectWithValue('detail' in payload && payload.detail ? payload.detail : '行情数据加载失败');
      }
      return payload as KLineResponse;
    } catch (error) {
      const message = error instanceof Error ? error.message : '网络异常，无法连接行情 API';
      return rejectWithValue(message);
    }
  },
);

const marketSlice = createSlice({
  name: 'market',
  initialState,
  reducers: {
    setSymbol(state, action: PayloadAction<string>) {
      state.symbol = action.payload.trim().toUpperCase();
    },
    clearError(state) {
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchKLineData.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchKLineData.fulfilled, (state, action) => {
        state.loading = false;
        state.symbol = action.payload.symbol;
        state.candles = action.payload.candles;
        state.markers = action.payload.markers;
        state.lastLoadedAt = Date.now();
      })
      .addCase(fetchKLineData.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload || action.error.message || '行情数据加载失败';
      });
  },
});

export const { setSymbol, clearError } = marketSlice.actions;
export default marketSlice.reducer;
