import { createSlice, type PayloadAction } from '@reduxjs/toolkit';

import { MA_COLORS, MA_WINDOW_MAX, MA_WINDOW_MIN } from '../config/chart';

export type Language = 'zh-CN' | 'en-US';
export type PriceScale = 'normal' | 'logarithmic';
export type CandleColorScheme = 'china' | 'international';

interface ChartConfigState {
  language: Language;
  priceScale: PriceScale;
  colorScheme: CandleColorScheme;
  // Keep MA window/color preferences even when the overlay is hidden.
  maVisible: boolean;
  maWindow: number;
  maColor: string;
}

const initialState: ChartConfigState = {
  language: 'zh-CN',
  priceScale: 'normal',
  colorScheme: 'china',
  maVisible: true,
  maWindow: 5,
  maColor: MA_COLORS[0],
};

const configSlice = createSlice({
  name: 'config',
  initialState,
  reducers: {
    setLanguage(state, action: PayloadAction<Language>) {
      state.language = action.payload;
    },
    setPriceScale(state, action: PayloadAction<PriceScale>) {
      state.priceScale = action.payload;
    },
    setColorScheme(state, action: PayloadAction<CandleColorScheme>) {
      state.colorScheme = action.payload;
    },
    setMaVisible(state, action: PayloadAction<boolean>) {
      state.maVisible = action.payload;
    },
    setMaWindow(state, action: PayloadAction<number>) {
      state.maWindow = Math.min(MA_WINDOW_MAX, Math.max(MA_WINDOW_MIN, action.payload));
    },
    setMaColor(state, action: PayloadAction<string>) {
      state.maColor = action.payload;
    },
  },
});

export const {
  setLanguage,
  setPriceScale,
  setColorScheme,
  setMaVisible,
  setMaWindow,
  setMaColor,
} = configSlice.actions;
export default configSlice.reducer;
