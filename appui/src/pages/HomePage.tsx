import { ExperimentOutlined, LineChartOutlined } from '@ant-design/icons';
import { Card, Col, Row, Space, Typography } from 'antd';
import { Link } from 'react-router-dom';

const modules = [
  {
    to: '/kline',
    title: 'KLine Module',
    description: 'Candlestick viewer with virtual loading, MA overlay and chart controls.',
    icon: <LineChartOutlined />,
  },
  {
    to: '/backtest',
    title: 'Backtest Module',
    description: 'Run MA cross strategy backtests and inspect trades, equity and metrics.',
    icon: <ExperimentOutlined />,
  },
];

export default function HomePage() {
  return (
    <section className="page page--home">
      <Space direction="vertical" size={24} className="home-shell">
        <div>
          <Typography.Title level={2}>Quant Workspace</Typography.Title>
          <Typography.Text type="secondary">
            Choose a module to inspect market data or run strategy research.
          </Typography.Text>
        </div>
        <Row gutter={[16, 16]}>
          {modules.map((item) => (
            <Col key={item.to} xs={24} md={12}>
              <Link className="module-link" to={item.to}>
                <Card hoverable className="module-card">
                  <Space align="start" size={16}>
                    <span className="module-card__icon">{item.icon}</span>
                    <Space direction="vertical" size={6}>
                      <Typography.Title level={4}>{item.title}</Typography.Title>
                      <Typography.Text type="secondary">{item.description}</Typography.Text>
                    </Space>
                  </Space>
                </Card>
              </Link>
            </Col>
          ))}
        </Row>
      </Space>
    </section>
  );
}
