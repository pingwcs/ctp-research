import { createSlice, type PayloadAction } from '@reduxjs/toolkit';

import { MA_COLORS } from '../config/chart';

export type Language = 'zh-CN' | 'en-US';
export type PriceScale = 'normal' | 'logarithmic';
export type CandleColorScheme = 'china' | 'international';

interface ChartConfigState {
  language: Language;
  priceScale: PriceScale;
  colorScheme: CandleColorScheme;
  maWindow: number;
  maColor: string;
}

const initialState: ChartConfigState = {
  language: 'zh-CN',
  priceScale: 'normal',
  colorScheme: 'china',
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
    setMaWindow(state, action: PayloadAction<number>) {
      state.maWindow = Math.min(30, Math.max(1, action.payload));
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
  setMaWindow,
  setMaColor,
} = configSlice.actions;
export default configSlice.reducer;
