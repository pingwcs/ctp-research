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
  Tooltip,
  Typography,
  type TableColumnsType,
} from 'antd';
import { useEffect, useMemo, useState, type MouseEvent } from 'react';

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

const TIME_FORMATTER = new Intl.DateTimeFormat('zh-CN', {
  timeZone: 'Asia/Shanghai',
  year: 'numeric',
  month: 'numeric',
  day: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
  second: '2-digit',
  hour12: false,
});

const MONEY_FORMATTER = new Intl.NumberFormat('zh-CN', {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const formatMetric = (value: number | null) => {
  if (value === null || Number.isNaN(value)) return '--';
  return Math.abs(value) < 1 ? `${(value * 100).toFixed(2)}%` : value.toFixed(4);
};

const formatTime = (value: number) => TIME_FORMATTER.format(new Date(value * 1000));
const formatMoney = (value: number) => MONEY_FORMATTER.format(value);

const EQUITY_CHART_WIDTH = 900;
const EQUITY_CHART_HEIGHT = 240;

type EquityChartPoint = EquityPoint & {
  x: number;
  y: number;
};

function EquityChart({ points }: { points: EquityPoint[] }) {
  const [activeIndex, setActiveIndex] = useState<number | null>(null);
  const chart = useMemo(() => {
    if (!points.length) {
      return {
        chartPoints: [] as EquityChartPoint[],
        polyline: '',
      };
    }

    const min = Math.min(...points.map((point) => point.equity));
    const max = Math.max(...points.map((point) => point.equity));
    const span = max - min || 1;
    const chartPoints = points.map((point, index) => {
      const x = (index / Math.max(1, points.length - 1)) * EQUITY_CHART_WIDTH;
      const y = EQUITY_CHART_HEIGHT - ((point.equity - min) / span) * EQUITY_CHART_HEIGHT;
      return { ...point, x, y };
    });

    return {
      chartPoints,
      polyline: chartPoints.map((point) => `${point.x},${point.y}`).join(' '),
    };
  }, [points]);

  if (!points.length) return <Empty description="No equity data" />;

  const activePoint = activeIndex === null ? null : (chart.chartPoints[activeIndex] ?? null);

  const updateActivePoint = (event: MouseEvent<HTMLDivElement>) => {
    if (chart.chartPoints.length <= 1) {
      setActiveIndex(0);
      return;
    }
    const rect = event.currentTarget.getBoundingClientRect();
    const ratio = Math.min(1, Math.max(0, (event.clientX - rect.left) / rect.width));
    setActiveIndex(Math.round(ratio * (chart.chartPoints.length - 1)));
  };

  return (
    <div
      className="equity-chart-shell"
      onMouseLeave={() => setActiveIndex(null)}
      onMouseMove={updateActivePoint}
    >
      <svg
        className="equity-chart"
        viewBox={`0 0 ${EQUITY_CHART_WIDTH} ${EQUITY_CHART_HEIGHT}`}
        role="img"
        aria-label="Equity curve"
        preserveAspectRatio="none"
      >
        <polyline
          fill="none"
          points={chart.polyline}
          stroke="#38bdf8"
          strokeLinecap="round"
          strokeWidth="3"
        />
        {activePoint ? (
          <>
            <line
              className="equity-chart__guide"
              x1={activePoint.x}
              x2={activePoint.x}
              y1="0"
              y2={EQUITY_CHART_HEIGHT}
            />
            <circle className="equity-chart__point" cx={activePoint.x} cy={activePoint.y} r="5" />
          </>
        ) : null}
      </svg>
      {activePoint ? (
        <Tooltip
          destroyOnHidden
          open
          placement="top"
          title={
            <div className="equity-tooltip">
              <div className="equity-tooltip__time">{formatTime(activePoint.time)}</div>
              <div className="equity-tooltip__grid">
                <span>Equity</span>
                <strong>{formatMoney(activePoint.equity)}</strong>
                <span>Cash</span>
                <strong>{formatMoney(activePoint.cash)}</strong>
                <span>Position</span>
                <strong>{activePoint.position.toLocaleString('zh-CN')}</strong>
              </div>
            </div>
          }
        >
          <span
            className="equity-chart__active-anchor"
            style={{
              left: `${(activePoint.x / EQUITY_CHART_WIDTH) * 100}%`,
              top: `${(activePoint.y / EQUITY_CHART_HEIGHT) * 100}%`,
            }}
          />
        </Tooltip>
      ) : null}
    </div>
  );
}

type TradeRow = BacktestTrade & {
  key: string;
};

const tradeColumns: TableColumnsType<TradeRow> = [
  {
    title: 'Time',
    dataIndex: 'time',
    render: (value: number) => formatTime(value),
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
];

export default function BacktestPage() {
  const dispatch = useAppDispatch();
  const state = useAppSelector((store) => store.backtest);
  const [tradePagination, setTradePagination] = useState({ current: 1, pageSize: 10 });

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
