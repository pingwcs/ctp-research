import ReloadOutlined from '@ant-design/icons/ReloadOutlined';
import SearchOutlined from '@ant-design/icons/SearchOutlined';
import SettingOutlined from '@ant-design/icons/SettingOutlined';
import Alert from 'antd/es/alert';
import Button from 'antd/es/button';
import Input from 'antd/es/input';
import Popover from 'antd/es/popover';
import Tooltip from 'antd/es/tooltip';
import Typography from 'antd/es/typography';
import { useMemo, useState, type FormEvent } from 'react';

import type { Candle } from '../api/market';
import KLineChart from '../components/KLineChart';
import {
  setColorScheme,
  setLanguage,
  setMaColor,
  setMaVisible,
  setMaWindow,
  setPriceScale,
} from '../store/configSlice';
import { useResponsiveProfile } from '../hooks/useResponsiveProfile';
import { useAppDispatch, useAppSelector } from '../store';
import KLineControls from './kline/KLineControls';
import { useKLineRangeRequests } from './kline/useKLineRangeRequests';

const PERIODS = ['1m', '5m', '15m', '1h', '4h', '1d'] as const;
type Period = (typeof PERIODS)[number];

interface MarketStats {
  latest: Candle | null;
  previous: Candle | null;
  change: number | null;
  changePct: number | null;
  high24: number | null;
  low24: number | null;
  volume24: number | null;
}

function normalizePairLabel(symbol: string) {
  const normalized = symbol.trim().toUpperCase();
  if (!normalized) return 'BTC/USDT';
  if (normalized.includes('/')) return normalized;
  if (normalized.endsWith('USDT')) return `${normalized.slice(0, -4)}/USDT`;
  return normalized === 'RB0909' ? 'BTC/USDT' : normalized;
}

function getMarketStats(candles: Candle[]): MarketStats {
  const latest = candles.length ? candles[candles.length - 1] : null;
  const previous = candles.length > 1 ? candles[candles.length - 2] : null;
  const recent = candles.slice(-96);
  const high24 = recent.length ? recent.reduce((max, item) => Math.max(max, item.high), recent[0].high) : null;
  const low24 = recent.length ? recent.reduce((min, item) => Math.min(min, item.low), recent[0].low) : null;
  const volume24 = recent.length ? recent.reduce((sum, item) => sum + item.volume, 0) : null;
  const change = latest && previous ? latest.close - previous.close : null;
  const changePct = latest && previous && previous.close ? (change! / previous.close) * 100 : null;

  return {
    latest,
    previous,
    change,
    changePct,
    high24,
    low24,
    volume24,
  };
}

function formatNumber(
  value: number | null | undefined,
  language: string,
  options: Intl.NumberFormatOptions = {},
) {
  if (typeof value !== 'number' || !Number.isFinite(value)) return '--';
  return new Intl.NumberFormat(language, {
    maximumFractionDigits: 2,
    minimumFractionDigits: 0,
    ...options,
  }).format(value);
}

function formatPercent(value: number | null | undefined, language: string) {
  if (typeof value !== 'number' || !Number.isFinite(value)) return '--';
  const formatted = new Intl.NumberFormat(language, {
    maximumFractionDigits: 2,
    minimumFractionDigits: 2,
  }).format(value);
  return `${value >= 0 ? '+' : ''}${formatted}%`;
}

export default function KLinePage() {
  const dispatch = useAppDispatch();
  const market = useAppSelector((state) => state.market);
  const config = useAppSelector((state) => state.config);
  const responsiveProfile = useResponsiveProfile();
  const [draftSymbol, setDraftSymbol] = useState(market.symbol);
  const [activePeriod, setActivePeriod] = useState<Period>('5m');

  const { loadSymbol, refresh, throttledRequestRange } = useKLineRangeRequests({
    lastRequestedRange: market.lastRequestedRange,
    loading: market.loading,
    symbol: market.symbol,
    total: market.total,
  });

  const submit = (event?: FormEvent<HTMLFormElement>) => {
    event?.preventDefault();
    loadSymbol(draftSymbol);
  };

  const pairLabel = normalizePairLabel(market.symbol);
  const stats = useMemo(() => getMarketStats(market.candles), [market.candles]);
  const isPositive = (stats.changePct ?? 0) >= 0;
  const latestPrice = stats.latest?.close ?? null;
  const watchRows = useMemo(
    () => [
      {
        symbol: pairLabel,
        label: market.symbol,
        price: latestPrice,
        changePct: stats.changePct,
        active: true,
      },
      {
        symbol: 'ETH/USDT',
        label: 'Spot',
        price: latestPrice ? latestPrice * 0.052 : null,
        changePct: stats.changePct !== null ? stats.changePct - 0.42 : null,
      },
      {
        symbol: 'SOL/USDT',
        label: 'Spot',
        price: latestPrice ? latestPrice * 0.0023 : null,
        changePct: stats.changePct !== null ? stats.changePct + 0.18 : null,
      },
      {
        symbol: 'BNB/USDT',
        label: 'Perp',
        price: latestPrice ? latestPrice * 0.0091 : null,
        changePct: stats.changePct !== null ? stats.changePct - 0.11 : null,
      },
    ],
    [latestPrice, market.symbol, pairLabel, stats.changePct],
  );

  return (
    <section className="page page--kline">
      <div className="kline-workspace">
        <aside className="market-panel">
          <div className="market-summary">
            <div className="market-summary__head">
              <span className="asset-orb">B</span>
              <div className="market-summary__identity">
                <Typography.Title level={2}>{pairLabel}</Typography.Title>
                <Typography.Text type="secondary">
                  Contract {market.symbol} . {market.total || market.candles.length} bars
                </Typography.Text>
              </div>
              <span className={isPositive ? 'change-pill is-up' : 'change-pill is-down'}>
                {formatPercent(stats.changePct, config.language)}
              </span>
            </div>

            <div className="market-summary__price-row">
              <strong>{formatNumber(latestPrice, config.language, { maximumFractionDigits: 4 })}</strong>
              <span className={isPositive ? 'price-delta is-up' : 'price-delta is-down'}>
                {stats.change !== null ? `${isPositive ? '+' : ''}${formatNumber(stats.change, config.language, { maximumFractionDigits: 4 })}` : '--'}
              </span>
            </div>

            <div className="market-stats">
              <div>
                <span>24H High</span>
                <strong>{formatNumber(stats.high24, config.language, { maximumFractionDigits: 4 })}</strong>
              </div>
              <div>
                <span>24H Low</span>
                <strong>{formatNumber(stats.low24, config.language, { maximumFractionDigits: 4 })}</strong>
              </div>
              <div>
                <span>24H Volume</span>
                <strong>{formatNumber(stats.volume24, config.language, { notation: 'compact' })}</strong>
              </div>
            </div>

            <div className="period-strip" aria-label="Chart interval">
              {PERIODS.map((period) => (
                <button
                  className={period === activePeriod ? 'period-chip is-active' : 'period-chip'}
                  key={period}
                  onClick={() => setActivePeriod(period)}
                  type="button"
                >
                  {period}
                </button>
              ))}
            </div>
          </div>

          <div className="market-tools">
            <form className="symbol-search" onSubmit={submit}>
              <Input
                className="symbol-input"
                onChange={(event) => setDraftSymbol(event.target.value)}
                placeholder="RB0909"
                spellCheck={false}
                value={draftSymbol}
              />
              <Tooltip title="Load symbol">
                <Button aria-label="Load symbol" htmlType="submit" icon={<SearchOutlined />} type="primary" />
              </Tooltip>
              <Tooltip title="Refresh">
                <Button aria-label="Refresh" icon={<ReloadOutlined spin={market.loading} />} onClick={refresh} />
              </Tooltip>
              <Popover
                content={
                  <KLineControls
                    colorScheme={config.colorScheme}
                    language={config.language}
                    maColor={config.maColor}
                    maVisible={config.maVisible}
                    maWindow={config.maWindow}
                    onColorSchemeChange={(value) => dispatch(setColorScheme(value))}
                    onLanguageChange={(value) => dispatch(setLanguage(value))}
                    onMaColorChange={(value) => dispatch(setMaColor(value))}
                    onMaVisibleChange={(value) => dispatch(setMaVisible(value))}
                    onMaWindowChange={(value) => dispatch(setMaWindow(value))}
                    onPriceScaleChange={(value) => dispatch(setPriceScale(value))}
                    priceScale={config.priceScale}
                  />
                }
                overlayClassName="settings-popover"
                placement="bottomLeft"
                trigger="click"
              >
                <Button aria-label="Chart settings" icon={<SettingOutlined />} />
              </Popover>
            </form>
            {market.error ? <Alert message={market.error} showIcon type="error" /> : null}
          </div>

          <section className="market-watch" aria-label="Market Watch">
            <div className="panel-heading">
              <Typography.Title level={4}>Market Watch</Typography.Title>
              <Typography.Text type="secondary">
                {market.lastLoadedTime ? new Date(market.lastLoadedTime).toLocaleTimeString(config.language) : 'Live'}
              </Typography.Text>
            </div>
            <div className="watch-table">
              {watchRows.map((row) => {
                const rowPositive = (row.changePct ?? 0) >= 0;
                return (
                  <button
                    className={row.active ? 'watch-row is-active' : 'watch-row'}
                    key={row.symbol}
                    type="button"
                  >
                    <span>
                      <strong>{row.symbol}</strong>
                      <small>{row.label}</small>
                    </span>
                    <span className="watch-row__price">
                      {formatNumber(row.price, config.language, { maximumFractionDigits: 4 })}
                    </span>
                    <span className={rowPositive ? 'watch-row__change is-up' : 'watch-row__change is-down'}>
                      {formatPercent(row.changePct, config.language)}
                    </span>
                  </button>
                );
              })}
            </div>
          </section>
        </aside>

        <main className="chart-panel">
          <KLineChart
            activePeriod={activePeriod}
            candles={market.candles}
            colorScheme={config.colorScheme}
            language={config.language}
            loading={market.loading}
            maColor={config.maColor}
            maVisible={config.maVisible}
            maWindow={config.maWindow}
            markers={market.markers}
            offset={market.offset}
            chartViewport={responsiveProfile.chartViewport}
            onRequestRange={throttledRequestRange}
            priceScale={config.priceScale}
            symbol={pairLabel}
            themeMode={config.themeMode}
            total={market.total}
          />
        </main>
      </div>
    </section>
  );
}
