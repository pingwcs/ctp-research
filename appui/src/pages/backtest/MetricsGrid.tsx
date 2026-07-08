import Card from 'antd/es/card';
import Col from 'antd/es/col';
import Row from 'antd/es/row';
import Statistic from 'antd/es/statistic';

const formatMetric = (value: number | null) => {
  if (value === null || Number.isNaN(value)) return '--';
  return Math.abs(value) < 1 ? `${(value * 100).toFixed(2)}%` : value.toFixed(4);
};

interface MetricsGridProps {
  metrics: Record<string, number | null>;
}

export default function MetricsGrid({ metrics }: MetricsGridProps) {
  return (
    <Row gutter={[12, 12]}>
      {Object.entries(metrics).map(([key, value]) => (
        <Col key={key} xs={12} md={8} xl={6}>
          <Card size="small">
            <Statistic title={key.replace(/_/g, ' ')} value={formatMetric(value)} />
          </Card>
        </Col>
      ))}
    </Row>
  );
}
