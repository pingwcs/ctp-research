import Space from 'antd/es/space';

import type { BacktestResult } from '../../api/backtest';
import EquityChart from '../../components/EquityChart';
import type { Language } from '../../store/configSlice';
import MetricsGrid from './MetricsGrid';
import TradesTable from './TradesTable';

interface BacktestResultsProps {
  language: Language;
  result: BacktestResult;
}

export default function BacktestResults({ language, result }: BacktestResultsProps) {
  return (
    <Space orientation="vertical" size={16} className="full-width">
      <EquityChart language={language} points={result.equity_curve} trades={result.trades} />
      <MetricsGrid metrics={result.metrics} />
      <TradesTable language={language} trades={result.trades} />
    </Space>
  );
}
