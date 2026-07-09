import type { BacktestTrade } from '../api/backtest';

export type TradeSide = BacktestTrade['side'];

interface TradePointStyle {
  className: string;
  color: string;
  label: string;
  shape: 'triangleDown' | 'triangleUp';
}

export const TRADE_MARKER_STYLES: Record<TradeSide, TradePointStyle> = {
  buy: {
    className: 'equity-trade-marker--buy',
    color: '#16a34a',
    label: 'Buy',
    shape: 'triangleUp',
  },
  sell: {
    className: 'equity-trade-marker--sell',
    color: '#dc2626',
    label: 'Sell',
    shape: 'triangleDown',
  },
};

export const TRADE_MARKER_SIZE = 8;
