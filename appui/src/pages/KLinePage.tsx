import { ReloadOutlined, SearchOutlined } from '@ant-design/icons';
import {
  Alert,
  Button,
  Card,
  Col,
  Form,
  Input,
  InputNumber,
  Row,
  Select,
  Space,
  Switch,
  Typography,
} from 'antd';
import { useCallback, useEffect, useMemo, useRef, useState, type FormEvent } from 'react';

import KLineChart from '../components/KLineChart';
import {
  CHART_RANGE_THROTTLE_MS,
  DEFAULT_KLINE_LIMIT,
  MA_COLORS,
  MA_WINDOW_MAX,
  MA_WINDOW_MIN,
} from '../config/chart';
import {
  LANGUAGE_OPTIONS,
  setColorScheme,
  setLanguage,
  setMaColor,
  setMaVisible,
  setMaWindow,
  setPriceScale,
  type CandleColorScheme,
  type Language,
  type PriceScale,
} from '../store/configSlice';
import { useResponsiveProfile } from '../hooks/useResponsiveProfile';
import { fetchKLineData, setSymbol } from '../store/marketSlice';
import { useAppDispatch, useAppSelector } from '../store';
import throttle from 'lodash/throttle';

const scaleOptions = [
  { value: 'normal', label: 'Normal' },
  { value: 'logarithmic', label: 'Logarithmic' },
];

const colorSchemeOptions = [
  { value: 'china', label: 'China' },
  { value: 'international', label: 'International' },
];

const languageOptions = LANGUAGE_OPTIONS.map((option) => ({ ...option }));

interface RangeRequestState {
  symbol: string;
  total: number;
  loading: boolean;
  lastRequestedRange: string | null;
}

export default function KLinePage() {
  const dispatch = useAppDispatch();
  const market = useAppSelector((state) => state.market);
  const config = useAppSelector((state) => state.config);
  const responsiveProfile = useResponsiveProfile();
  const [draftSymbol, setDraftSymbol] = useState(market.symbol);
  const initialSymbolRef = useRef(market.symbol);
  const pendingRangeRef = useRef<string | null>(null);
  const rangeRequestInFlightRef = useRef(false);
  const requestStateRef = useRef<RangeRequestState>({
    symbol: market.symbol,
    total: market.total,
    loading: market.loading,
    lastRequestedRange: market.lastRequestedRange,
  });

  useEffect(() => {
    void dispatch(fetchKLineData({ symbol: initialSymbolRef.current, limit: DEFAULT_KLINE_LIMIT }));
  }, [dispatch]);

  useEffect(() => {
    requestStateRef.current = {
      symbol: market.symbol,
      total: market.total,
      loading: market.loading,
      lastRequestedRange: market.lastRequestedRange,
    };
  }, [market.lastRequestedRange, market.loading, market.symbol, market.total]);

  useEffect(() => {
    if (!market.loading) {
      rangeRequestInFlightRef.current = false;
    }
  }, [market.loading, market.lastRequestedRange]);

  const submit = (event?: FormEvent<HTMLFormElement>) => {
    event?.preventDefault();
    const nextSymbol = draftSymbol.trim().toUpperCase();
    if (!nextSymbol) return;
    pendingRangeRef.current = null;
    rangeRequestInFlightRef.current = false;
    dispatch(setSymbol(nextSymbol));
    void dispatch(fetchKLineData({ symbol: nextSymbol, limit: DEFAULT_KLINE_LIMIT }));
  };

  const refresh = () => {
    pendingRangeRef.current = null;
    rangeRequestInFlightRef.current = false;
    void dispatch(fetchKLineData({ symbol: market.symbol, limit: DEFAULT_KLINE_LIMIT }));
  };

  const requestRange = useCallback(
    (left: number, right: number) => {
      const state = requestStateRef.current;
      if (!state.total || state.loading || rangeRequestInFlightRef.current) return;

      // The chart emits a global preload window; the page de-duplicates it
      // before hitting the market API so wheel/drag gestures stay cheap.
      const requestKey = `${left}:${right - left + 1}`;
      if (pendingRangeRef.current === requestKey || state.lastRequestedRange === requestKey) return;

      pendingRangeRef.current = requestKey;
      rangeRequestInFlightRef.current = true;
      void dispatch(
        fetchKLineData({ symbol: state.symbol, offset: left, limit: right - left + 1 }),
      );
    },
    [dispatch],
  );

  const throttledRequestRange = useMemo(
    () => throttle(requestRange, CHART_RANGE_THROTTLE_MS, { trailing: false }),
    [requestRange],
  );

  useEffect(() => () => throttledRequestRange.cancel(), [throttledRequestRange]);

  return (
    <section className="page page--kline">
      <Space orientation="vertical" size={16} className="page-stack">
        <Card className="toolbar-card">
          <Row align="bottom" gutter={[12, 12]} justify="space-between">
            <Col xs={24} lg={8}>
              <Typography.Title level={3}>Futures K-Line</Typography.Title>
              <Typography.Text type="secondary">
                {market.candles.length
                  ? `${market.symbol} / ${market.total.toLocaleString(config.language)} total bars`
                  : market.symbol}
              </Typography.Text>
            </Col>
            <Col xs={24} lg={16}>
              <Form component="form" layout="inline" onSubmitCapture={submit}>
                <Form.Item className="symbol-form-item">
                  <Input
                    className="symbol-input"
                    onChange={(event) => setDraftSymbol(event.target.value)}
                    placeholder="RB0909"
                    spellCheck={false}
                    value={draftSymbol}
                  />
                </Form.Item>
                <Form.Item>
                  <Button
                    // disabled={market.loading}
                    htmlType="submit"
                    icon={<SearchOutlined />}
                    type="primary"
                  />
                </Form.Item>
                <Form.Item>
                  <Button
                    // disabled={market.loading}
                    icon={<ReloadOutlined />}
                    onClick={refresh}
                  />
                </Form.Item>
              </Form>
            </Col>
          </Row>
        </Card>

        <Card className="control-card">
          <Row gutter={[12, 12]}>
            <Col xs={12} md={6} xl={4}>
              <Typography.Text type="secondary">Scale</Typography.Text>
              <Select
                className="full-width"
                onChange={(value) => dispatch(setPriceScale(value as PriceScale))}
                options={scaleOptions}
                value={config.priceScale}
              />
            </Col>
            <Col xs={12} md={6} xl={4}>
              <Typography.Text type="secondary">Bar Color</Typography.Text>
              <Select
                className="full-width"
                onChange={(value) => dispatch(setColorScheme(value as CandleColorScheme))}
                options={colorSchemeOptions}
                value={config.colorScheme}
              />
            </Col>
            <Col xs={12} md={6} xl={4}>
              <Typography.Text type="secondary">Language</Typography.Text>
              <Select
                className="full-width"
                onChange={(value) => dispatch(setLanguage(value as Language))}
                options={languageOptions}
                value={config.language}
              />
            </Col>
            <Col xs={12} md={6} xl={4}>
              <Typography.Text type="secondary">MA</Typography.Text>
              <div>
                <Switch
                  checked={config.maVisible}
                  onChange={(checked) => dispatch(setMaVisible(checked))}
                />
              </div>
            </Col>
            <Col xs={12} md={6} xl={4}>
              <Typography.Text type="secondary">MA Window</Typography.Text>
              <InputNumber
                className="full-width"
                disabled={!config.maVisible}
                max={MA_WINDOW_MAX}
                min={MA_WINDOW_MIN}
                onChange={(value) => dispatch(setMaWindow(Number(value || 1)))}
                value={config.maWindow}
              />
            </Col>
            <Col xs={24} xl={4}>
              <Typography.Text type="secondary">MA Color</Typography.Text>
              <Space className="ma-color-row" wrap>
                {MA_COLORS.map((color) => (
                  <Button
                    aria-label={`MA color ${color}`}
                    className={config.maColor === color ? 'color-swatch is-active' : 'color-swatch'}
                    disabled={!config.maVisible}
                    key={color}
                    onClick={() => dispatch(setMaColor(color))}
                    shape="circle"
                    style={{ backgroundColor: color }}
                  />
                ))}
              </Space>
            </Col>
          </Row>
        </Card>

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

        <div className="page-footer">
          <Typography.Text type="secondary">Data API: /api/market/kline</Typography.Text>
          <Typography.Text type="secondary">
            {market.lastLoadedTime
              ? new Date(market.lastLoadedTime).toLocaleString(config.language)
              : ''}
          </Typography.Text>
        </div>
      </Space>
    </section>
  );
}
