import ExperimentOutlined from '@ant-design/icons/ExperimentOutlined';
import HomeOutlined from '@ant-design/icons/HomeOutlined';
import LineChartOutlined from '@ant-design/icons/LineChartOutlined';
import Layout from 'antd/es/layout';
import Menu from 'antd/es/menu';
import Typography from 'antd/es/typography';
import { lazy, Suspense, useEffect } from 'react';
import { Navigate, Route, Routes, useLocation, useNavigate } from 'react-router-dom';

import { useAppSelector } from './store';

const { Header, Content } = Layout;

const HomePage = lazy(() => import('./pages/HomePage'));
const KLinePage = lazy(() => import('./pages/KLinePage'));
const BacktestPage = lazy(() => import('./pages/BacktestPage'));

const navItems = [
  { key: '/', label: 'Home', icon: <HomeOutlined /> },
  { key: '/kline', label: 'KLine', icon: <LineChartOutlined /> },
  { key: '/backtest', label: 'Backtest', icon: <ExperimentOutlined /> },
];

export default function App() {
  const location = useLocation();
  const navigate = useNavigate();
  const language = useAppSelector((state) => state.config.language);

  useEffect(() => {
    document.documentElement.lang = language;
  }, [language]);

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
        <Suspense fallback={<div className="route-loading" />}>
          <Routes>
            <Route element={<HomePage />} path="/" />
            <Route element={<KLinePage />} path="/kline" />
            <Route element={<BacktestPage />} path="/backtest" />
            <Route element={<Navigate replace to="/" />} path="*" />
          </Routes>
        </Suspense>
      </Content>
    </Layout>
  );
}
