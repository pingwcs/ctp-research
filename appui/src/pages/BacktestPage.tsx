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
import { useEffect } from 'react';

import type { BacktestTrade, EquityPoint } from '../api/backtest';
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

const formatMetric = (value: number | null) => {
  if (value === null || Number.isNaN(value)) return '--';
  return Math.abs(value) < 1 ? `${(value * 100).toFixed(2)}%` : value.toFixed(4);
};

function EquityChart({ points }: { points: EquityPoint[] }) {
  if (!points.length) return <Empty description="No equity data" />;
  const width = 900;
  const height = 240;
  const min = Math.min(...points.map((point) => point.equity));
  const max = Math.max(...points.map((point) => point.equity));
  const span = max - min || 1;
  const polyline = points
    .map((point, index) => {
      const x = (index / Math.max(1, points.length - 1)) * width;
      const y = height - ((point.equity - min) / span) * height;
      return `${x},${y}`;
    })
    .join(' ');

  return (
    <svg className="equity-chart" viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Equity curve">
      <polyline fill="none" points={polyline} stroke="#38bdf8" strokeLinecap="round" strokeWidth="3" />
    </svg>
  );
}

const tradeColumns: TableColumnsType<BacktestTrade> = [
  {
    title: 'Time',
    dataIndex: 'time',
    render: (value: number) => new Date(value * 1000).toLocaleString(),
  },
  {
    title: 'Side',
    dataIndex: 'side',
    render: (value: BacktestTrade['side']) => (
      <Typography.Text type={value === 'buy' ? 'danger' : 'success'}>
        {value}
      </Typography.Text>
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
];

export default function BacktestPage() {
  const dispatch = useAppDispatch();
  const state = useAppSelector((store) => store.backtest);

  useEffect(() => {
    void dispatch(fetchBacktestOptions());
  }, [dispatch]);

  const submit = () => {
    if (!state.selectedSymbol || !state.selectedStrategy) return;
    void dispatch(runBacktest({
      symbol: state.selectedSymbol,
      strategy: state.selectedStrategy,
      start_time: state.startTime || null,
      end_time: state.endTime || null,
      metrics: state.selectedMetrics,
    }));
  };

  return (
    <section className="page page--backtest">
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={7}>
          <Card
            className="tool-card"
            extra={(
              <Button
                icon={<ReloadOutlined spin={state.loadingOptions} />}
                onClick={() => void dispatch(fetchBacktestOptions())}
              />
            )}
            title="Backtest"
          >
            <Space direction="vertical" size={14} className="full-width">
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
            title="Results"
            extra={state.result ? `${state.result.symbol} · ${state.result.trades.length} trades` : null}
          >
            {state.result ? (
              <Space direction="vertical" size={16} className="full-width">
                <EquityChart points={state.result.equity_curve} />

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
                  dataSource={state.result.trades.slice(-80)}
                  pagination={{ pageSize: 10, size: 'small' }}
                  rowKey={(trade, index) => `${trade.time}-${trade.side}-${index}`}
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
