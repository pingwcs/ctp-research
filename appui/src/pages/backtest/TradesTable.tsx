import Table from 'antd/es/table';
import type { ColumnsType } from 'antd/es/table';
import Typography from 'antd/es/typography';
import { useEffect, useMemo, useState } from 'react';

import type { BacktestTrade } from '../../api/backtest';
import { CHART_TIME_ZONE } from '../../config/chart';
import type { Language } from '../../store/configSlice';

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

type TradeRow = BacktestTrade & {
  key: string;
};

const createTimeFormatter = (language: Language) =>
  new Intl.DateTimeFormat(language, TIME_FORMAT_OPTIONS);

const formatTime = (value: number, formatter: Intl.DateTimeFormat) =>
  formatter.format(new Date(value * 1000));

interface TradesTableProps {
  language: Language;
  trades: BacktestTrade[];
}

export default function TradesTable({ language, trades }: TradesTableProps) {
  const [pagination, setPagination] = useState({ current: 1, pageSize: 10 });
  const timeFormatter = useMemo(() => createTimeFormatter(language), [language]);
  const rows = useMemo<TradeRow[]>(
    () =>
      trades.map((trade, index) => ({
        ...trade,
        key: `${index}-${trade.time}-${trade.side}`,
      })),
    [trades],
  );
  const columns = useMemo<ColumnsType<TradeRow>>(
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

  useEffect(() => {
    setPagination((current) => ({ ...current, current: 1 }));
  }, [trades]);

  return (
    <Table
      columns={columns}
      dataSource={rows}
      pagination={{
        current: pagination.current,
        onChange: (current, pageSize) => setPagination({ current, pageSize }),
        pageSize: pagination.pageSize,
        pageSizeOptions: ['10', '20', '50', '100'],
        showSizeChanger: true,
        showTotal: (total, range) => `${range[0]}-${range[1]} / ${total}`,
        size: 'small',
        total: rows.length,
      }}
      rowKey="key"
      scroll={{ x: 720 }}
      size="small"
    />
  );
}
