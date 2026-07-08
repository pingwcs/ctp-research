import Alert from 'antd/es/alert';
import Space from 'antd/es/space';
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
import KLineStatusFooter from './kline/KLineStatusFooter';
import KLineToolbar from './kline/KLineToolbar';
import { useKLineRangeRequests } from './kline/useKLineRangeRequests';

export default function KLinePage() {
  const dispatch = useAppDispatch();
  const market = useAppSelector((state) => state.market);
  const config = useAppSelector((state) => state.config);
  const responsiveProfile = useResponsiveProfile();
  const [draftSymbol, setDraftSymbol] = useState(market.symbol);

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

  return (
    <section className="page page--kline">
      <Space orientation="vertical" size={16} className="page-stack">
        <KLineToolbar
          candlesCount={market.candles.length}
          draftSymbol={draftSymbol}
          language={config.language}
          onDraftSymbolChange={setDraftSymbol}
          onRefresh={refresh}
          onSubmit={submit}
          symbol={market.symbol}
          total={market.total}
        />

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

        {market.error ? <Alert message={market.error} showIcon type="error" /> : null}

        <KLineChart
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
          symbol={market.symbol}
          total={market.total}
        />

        <KLineStatusFooter language={config.language} lastLoadedTime={market.lastLoadedTime} />
      </Space>
    </section>
  );
}
