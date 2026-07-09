import Space from 'antd/es/space';
import Switch from 'antd/es/switch';
import Typography from 'antd/es/typography';
import { useState } from 'react';

import type { BacktestResult } from '../../api/backtest';
import EquityChart from '../../components/EquityChart';
import type { Language } from '../../store/configSlice';
import type { ThemeMode } from '../../config/theme';
import MetricsGrid from './MetricsGrid';
import TradesTable from './TradesTable';

interface BacktestResultsProps {
  language: Language;
  result: BacktestResult;
  themeMode: ThemeMode;
}

export default function BacktestResults({ language, result, themeMode }: BacktestResultsProps) {
  const [showTradeMarkers, setShowTradeMarkers] = useState(false);

  return (
    <Space orientation="vertical" size={16} className="full-width">
      <div className="backtest-chart-toolbar">
        <Typography.Text strong>Equity Curve</Typography.Text>
        <Space size={8}>
          <Typography.Text type="secondary">Trade points</Typography.Text>
          <Switch checked={showTradeMarkers} onChange={setShowTradeMarkers} size="small" />
        </Space>
      </div>
      <EquityChart
        language={language}
        points={result.equity_curve}
        showTradeMarkers={showTradeMarkers}
        themeMode={themeMode}
        trades={result.trades}
      />
      <MetricsGrid metrics={result.metrics} />
      <TradesTable language={language} trades={result.trades} />
    </Space>
  );
}
