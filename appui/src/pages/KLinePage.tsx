import ReloadOutlined from '@ant-design/icons/ReloadOutlined';
import SearchOutlined from '@ant-design/icons/SearchOutlined';
import SettingOutlined from '@ant-design/icons/SettingOutlined';
import Alert from 'antd/es/alert';
import Button from 'antd/es/button';
import Input from 'antd/es/input';
import Popover from 'antd/es/popover';
import Tooltip from 'antd/es/tooltip';
import { useState, type FormEvent } from 'react';

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

function normalizePairLabel(symbol: string) {
  const normalized = symbol.trim().toUpperCase();
  if (!normalized) return 'BTC/USDT';
  if (normalized.includes('/')) return normalized;
  if (normalized.endsWith('USDT')) return `${normalized.slice(0, -4)}/USDT`;
  return normalized === 'RB0909' ? 'BTC/USDT' : normalized;
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

  return (
    <section className="page page--kline">
      <div className="kline-workspace">
        <div className="market-tools kline-toolbar">
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
          {market.error ? <Alert message={market.error} showIcon type="error" /> : null}
        </div>

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
