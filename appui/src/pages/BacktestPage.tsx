import { PlayCircleOutlined, ReloadOutlined } from '@ant-design/icons';
import {
  Alert,
  Button,
  Card,
  Col,
  Empty,
  Input,
  Row,
  Select,
  Space,
  Statistic,
  Table,
  Typography,
  type TableColumnsType,
} from 'antd';
import { useEffect, useMemo, useState } from 'react';

import type { BacktestTrade } from '../api/backtest';
import EquityChart from '../components/EquityChart';
import { CHART_TIME_ZONE } from '../config/chart';
import {
  fetchBacktestOptions,
  runBacktest,
  setEndTime,
  setSelectedMetrics,
  setSelectedStrategy,
  setSelectedSymbol,
  setStartTime,
} from '../store/backtestSlice';
import { useAppDispatch, useAppSelector } from '../store';
import type { Language } from '../store/configSlice';

const TIME_FORMAT_OPTIONS: Intl.DateTimeFormatOptions = {
  timeZone: CHART_TIME_ZONE,
  year: 'numeric',
  month: 'numeric',
  day: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
  second: '2-digit',
  hour12: false,
};

const formatMetric = (value: number | null) => {
  if (value === null || Number.isNaN(value)) return '--';
  return Math.abs(value) < 1 ? `${(value * 100).toFixed(2)}%` : value.toFixed(4);
};

const createTimeFormatter = (language: Language) =>
  new Intl.DateTimeFormat(language, TIME_FORMAT_OPTIONS);

const formatTime = (value: number, formatter: Intl.DateTimeFormat) =>
  formatter.format(new Date(value * 1000));

type TradeRow = BacktestTrade & {
  key: string;
};

export default function BacktestPage() {
  const dispatch = useAppDispatch();
  const state = useAppSelector((store) => store.backtest);
  const language = useAppSelector((store) => store.config.language);
  const [tradePagination, setTradePagination] = useState({ current: 1, pageSize: 10 });
  const timeFormatter = useMemo(() => createTimeFormatter(language), [language]);
  const tradeColumns = useMemo<TableColumnsType<TradeRow>>(
    () => [
      {
        title: 'Time',
        dataIndex: 'time',
        render: (value: number) => formatTime(value, timeFormatter),
      },
      {
        title: 'Side',
        dataIndex: 'side',
        render: (value: BacktestTrade['side']) => (
          <Typography.Text type={value === 'buy' ? 'danger' : 'success'}>{value}</Typography.Text>
        ),
      },
      {
        title: 'Price',
        dataIndex: 'price',
        align: 'right',
        render: (value: number) => value.toFixed(2),
      },
      {
        title: 'Qty',
        dataIndex: 'quantity',
        align: 'right',
      },
      {
        title: 'Reason',
        dataIndex: 'reason',
      },
    ],
    [timeFormatter],
  );

  const tradeRows = useMemo<TradeRow[]>(
    () =>
      state.result?.trades.map((trade, index) => ({
        ...trade,
        key: `${index}-${trade.time}-${trade.side}`,
      })) ?? [],
    [state.result],
  );

  useEffect(() => {
    void dispatch(fetchBacktestOptions());
  }, [dispatch]);

  useEffect(() => {
    setTradePagination((pagination) => ({ ...pagination, current: 1 }));
  }, [state.result]);

  const submit = () => {
    if (!state.selectedSymbol || !state.selectedStrategy) return;
    void dispatch(
      runBacktest({
        symbol: state.selectedSymbol,
        strategy: state.selectedStrategy,
        start_time: state.startTime || null,
        end_time: state.endTime || null,
        metrics: state.selectedMetrics,
      }),
    );
  };

  return (
    <section className="page page--backtest">
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={7}>
          <Card
            className="tool-card"
            extra={
              <Button
                icon={<ReloadOutlined spin={state.loadingOptions} />}
                onClick={() => void dispatch(fetchBacktestOptions())}
              />
            }
            title="Backtest"
          >
            <Space orientation="vertical" size={14} className="full-width">
              <div>
                <Typography.Text type="secondary">Strategy</Typography.Text>
                <Select
                  className="full-width"
                  loading={state.loadingOptions}
                  onChange={(value) => dispatch(setSelectedStrategy(value))}
                  options={state.strategies.map((strategy) => ({
                    value: strategy.id,
                    label: strategy.name,
                  }))}
                  value={state.selectedStrategy}
                />
              </div>

              <div>
                <Typography.Text type="secondary">Symbol</Typography.Text>
                <Select
                  className="full-width"
                  loading={state.loadingOptions}
                  onChange={(value) => dispatch(setSelectedSymbol(value))}
                  options={state.symbols.map((symbol) => ({
                    value: symbol,
                    label: symbol,
                  }))}
                  value={state.selectedSymbol || undefined}
                />
              </div>

              <Row gutter={10}>
                <Col xs={24} sm={12} lg={24} xl={12}>
                  <Typography.Text type="secondary">Start</Typography.Text>
                  <Input
                    onChange={(event) => dispatch(setStartTime(event.target.value))}
                    type="datetime-local"
                    value={state.startTime}
                  />
                </Col>
                <Col xs={24} sm={12} lg={24} xl={12}>
                  <Typography.Text type="secondary">End</Typography.Text>
                  <Input
                    onChange={(event) => dispatch(setEndTime(event.target.value))}
                    type="datetime-local"
                    value={state.endTime}
                  />
                </Col>
              </Row>

              <div>
                <Typography.Text type="secondary">Metrics</Typography.Text>
                <Select
                  className="full-width"
                  mode="multiple"
                  onChange={(value) => dispatch(setSelectedMetrics(value))}
                  options={state.metrics.map((metric) => ({
                    value: metric.id,
                    label: metric.name,
                  }))}
                  value={state.selectedMetrics}
                />
              </div>

              {state.error ? <Alert message={state.error} showIcon type="error" /> : null}

              <Button
                block
                disabled={!state.selectedSymbol}
                icon={<PlayCircleOutlined />}
                loading={state.running}
                onClick={submit}
                type="primary"
              >
                Run Backtest
              </Button>
            </Space>
          </Card>
        </Col>

        <Col xs={24} lg={17}>
          <Card
            className="result-card"
            extra={state.result ? `${state.result.symbol} . ${tradeRows.length} trades` : null}
            title="Results"
          >
            {state.result ? (
              <Space orientation="vertical" size={16} className="full-width">
                <EquityChart language={language} points={state.result.equity_curve} />

                <Row gutter={[12, 12]}>
                  {Object.entries(state.result.metrics).map(([key, value]) => (
                    <Col key={key} xs={12} md={8} xl={6}>
                      <Card size="small">
                        <Statistic title={key.replace(/_/g, ' ')} value={formatMetric(value)} />
                      </Card>
                    </Col>
                  ))}
                </Row>

                <Table
                  columns={tradeColumns}
                  dataSource={tradeRows}
                  pagination={{
                    current: tradePagination.current,
                    onChange: (current, pageSize) => setTradePagination({ current, pageSize }),
                    pageSize: tradePagination.pageSize,
                    pageSizeOptions: ['10', '20', '50', '100'],
                    showSizeChanger: true,
                    showTotal: (total, range) => `${range[0]}-${range[1]} / ${total}`,
                    size: 'small',
                    total: tradeRows.length,
                  }}
                  rowKey="key"
                  scroll={{ x: 720 }}
                  size="small"
                />
              </Space>
            ) : (
              <Empty description="No backtest result" />
            )}
          </Card>
        </Col>
      </Row>
    </section>
  );
}
