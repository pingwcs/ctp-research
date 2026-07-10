import PlayCircleOutlined from '@ant-design/icons/PlayCircleOutlined';
import ReloadOutlined from '@ant-design/icons/ReloadOutlined';
import Alert from 'antd/es/alert';
import Button from 'antd/es/button';
import Card from 'antd/es/card';
import Col from 'antd/es/col';
import DatePicker from 'antd/es/date-picker';
import Empty from 'antd/es/empty';
import Row from 'antd/es/row';
import Select from 'antd/es/select';
import Space from 'antd/es/space';
import Typography from 'antd/es/typography';
import { lazy, Suspense, useEffect } from 'react';

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

const BacktestResults = lazy(() => import('./backtest/BacktestResults'));
const BACKTEST_DATE_TIME_FORMAT = 'YYYY-MM-DD HH:mm';

function toBacktestDateTime(value: string | string[] | null) {
  const dateTime = Array.isArray(value) ? value[0] : value;
  return dateTime ? dateTime.replace(' ', 'T') : '';
}

export default function BacktestPage() {
  const dispatch = useAppDispatch();
  const state = useAppSelector((store) => store.backtest);
  const { language, themeMode } = useAppSelector((store) => store.config);

  useEffect(() => {
    void dispatch(fetchBacktestOptions());
  }, [dispatch]);

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
                  value={state.selectedStrategy || undefined}
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
                  <DatePicker
                    className="full-width"
                    format={BACKTEST_DATE_TIME_FORMAT}
                    onChange={(_, dateString) => dispatch(setStartTime(toBacktestDateTime(dateString)))}
                    placeholder="Start"
                    showTime={{ format: 'HH:mm' }}
                  />
                </Col>
                <Col xs={24} sm={12} lg={24} xl={12}>
                  <Typography.Text type="secondary">End</Typography.Text>
                  <DatePicker
                    className="full-width"
                    format={BACKTEST_DATE_TIME_FORMAT}
                    onChange={(_, dateString) => dispatch(setEndTime(toBacktestDateTime(dateString)))}
                    placeholder="End"
                    showTime={{ format: 'HH:mm' }}
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

              {state.running && state.jobStatus ? (
                <Typography.Text type="secondary">
                  Job {state.activeJobId || 'pending'} . {state.jobStatus}
                </Typography.Text>
              ) : null}

              <Button
                block
                disabled={!state.selectedSymbol || !state.selectedStrategy}
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
            extra={
              state.result ? `${state.result.symbol} . ${state.result.trades.length} trades` : null
            }
            title="Results"
          >
            {state.result ? (
              <Suspense fallback={<Empty description="Loading results" />}>
                <BacktestResults language={language} result={state.result} themeMode={themeMode} />
              </Suspense>
            ) : (
              <Empty description="No backtest result" />
            )}
          </Card>
        </Col>
      </Row>
    </section>
  );
}
