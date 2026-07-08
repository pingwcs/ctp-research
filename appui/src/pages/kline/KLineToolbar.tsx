import ReloadOutlined from '@ant-design/icons/ReloadOutlined';
import SearchOutlined from '@ant-design/icons/SearchOutlined';
import Button from 'antd/es/button';
import Card from 'antd/es/card';
import Col from 'antd/es/col';
import Form from 'antd/es/form';
import Input from 'antd/es/input';
import Row from 'antd/es/row';
import Typography from 'antd/es/typography';
import type { FormEventHandler } from 'react';

import type { Language } from '../../store/configSlice';

interface KLineToolbarProps {
  candlesCount: number;
  draftSymbol: string;
  language: Language;
  onDraftSymbolChange: (value: string) => void;
  onRefresh: () => void;
  onSubmit: FormEventHandler<HTMLFormElement>;
  symbol: string;
  total: number;
}

export default function KLineToolbar({
  candlesCount,
  draftSymbol,
  language,
  onDraftSymbolChange,
  onRefresh,
  onSubmit,
  symbol,
  total,
}: KLineToolbarProps) {
  return (
    <Card className="toolbar-card">
      <Row align="bottom" gutter={[12, 12]} justify="space-between">
        <Col xs={24} lg={8}>
          <Typography.Title level={3}>Futures K-Line</Typography.Title>
          <Typography.Text type="secondary">
            {candlesCount ? `${symbol} / ${total.toLocaleString(language)} total bars` : symbol}
          </Typography.Text>
        </Col>
        <Col xs={24} lg={16}>
          <Form component="form" layout="inline" onSubmitCapture={onSubmit}>
            <Form.Item className="symbol-form-item">
              <Input
                className="symbol-input"
                onChange={(event) => onDraftSymbolChange(event.target.value)}
                placeholder="RB0909"
                spellCheck={false}
                value={draftSymbol}
              />
            </Form.Item>
            <Form.Item>
              <Button htmlType="submit" icon={<SearchOutlined />} type="primary" />
            </Form.Item>
            <Form.Item>
              <Button icon={<ReloadOutlined />} onClick={onRefresh} />
            </Form.Item>
          </Form>
        </Col>
      </Row>
    </Card>
  );
}
