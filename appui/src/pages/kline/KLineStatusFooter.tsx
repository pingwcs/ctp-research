import Typography from 'antd/es/typography';

import type { Language } from '../../store/configSlice';

interface KLineStatusFooterProps {
  language: Language;
  lastLoadedTime: number | null;
}

export default function KLineStatusFooter({ language, lastLoadedTime }: KLineStatusFooterProps) {
  return (
    <div className="page-footer">
      <Typography.Text type="secondary">Data API: /api/market/kline</Typography.Text>
      <Typography.Text type="secondary">
        {lastLoadedTime ? new Date(lastLoadedTime).toLocaleString(language) : ''}
      </Typography.Text>
    </div>
  );
}
