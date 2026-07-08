import { ExperimentOutlined, HomeOutlined, LineChartOutlined } from '@ant-design/icons';
import { Layout, Menu, Typography } from 'antd';
import { Navigate, Route, Routes, useLocation, useNavigate } from 'react-router-dom';

import BacktestPage from './pages/BacktestPage';
import HomePage from './pages/HomePage';
import KLinePage from './pages/KLinePage';

const { Header, Content } = Layout;

const navItems = [
  { key: '/', label: 'Home', icon: <HomeOutlined /> },
  { key: '/kline', label: 'KLine', icon: <LineChartOutlined /> },
  { key: '/backtest', label: 'Backtest', icon: <ExperimentOutlined /> },
];

export default function App() {
  const location = useLocation();
  const navigate = useNavigate();

  return (
    <Layout className="app-layout">
      <Header className="app-header">
        <Typography.Title className="app-brand" level={4}>
          FutureData
        </Typography.Title>
        <Menu
          className="app-menu"
          items={navItems}
          mode="horizontal"
          onClick={({ key }) => navigate(key)}
          selectedKeys={[location.pathname]}
          theme="dark"
        />
      </Header>
      <Content className="app-content">
        <Routes>
          <Route element={<HomePage />} path="/" />
          <Route element={<KLinePage />} path="/kline" />
          <Route element={<BacktestPage />} path="/backtest" />
          <Route element={<Navigate replace to="/" />} path="*" />
        </Routes>
      </Content>
    </Layout>
  );
}
