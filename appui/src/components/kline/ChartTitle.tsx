import UndoOutlined from '@ant-design/icons/UndoOutlined';
import Button from 'antd/es/button';
import Tooltip from 'antd/es/tooltip';
import Typography from 'antd/es/typography';

interface ChartTitleProps {
  candlesCount: number;
  maVisible: boolean;
  maWindow: number;
  offset: number;
  onResetTimeScale: () => void;
  symbol: string;
  total: number;
}

export default function ChartTitle({
  candlesCount,
  maVisible,
  maWindow,
  offset,
  onResetTimeScale,
  symbol,
  total,
}: ChartTitleProps) {
  return (
    <div className="chart-title">
      <div className="chart-title__main">
        <Typography.Text className="chart-title__symbol">{symbol}</Typography.Text>
        <Typography.Text className="chart-title__meta" type="secondary">
          5min OHLCV . {offset + 1}-{offset + candlesCount} / {total || candlesCount}
        </Typography.Text>
      </div>
      <div className="chart-title__actions">
        <Typography.Text className="chart-title__status" type="secondary">
          {`${candlesCount} bars . ${maVisible ? `MA${maWindow}` : 'MA off'}`}
        </Typography.Text>
        <Tooltip title="Restore zoom">
          <Button
            aria-label="Restore zoom"
            className="chart-icon-button"
            icon={<UndoOutlined />}
            onClick={onResetTimeScale}
            size="small"
            type="text"
          />
        </Tooltip>
      </div>
    </div>
  );
}
