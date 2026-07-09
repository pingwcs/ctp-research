import AppstoreOutlined from '@ant-design/icons/AppstoreOutlined';
import BellOutlined from '@ant-design/icons/BellOutlined';
import ExperimentOutlined from '@ant-design/icons/ExperimentOutlined';
import HomeOutlined from '@ant-design/icons/HomeOutlined';
import LineChartOutlined from '@ant-design/icons/LineChartOutlined';
import MoonOutlined from '@ant-design/icons/MoonOutlined';
import SettingOutlined from '@ant-design/icons/SettingOutlined';
import SunOutlined from '@ant-design/icons/SunOutlined';
import SwapOutlined from '@ant-design/icons/SwapOutlined';
import ThunderboltOutlined from '@ant-design/icons/ThunderboltOutlined';
import UserOutlined from '@ant-design/icons/UserOutlined';
import WalletOutlined from '@ant-design/icons/WalletOutlined';
import Avatar from 'antd/es/avatar';
import Button from 'antd/es/button';
import Layout from 'antd/es/layout';
import Tooltip from 'antd/es/tooltip';
import Typography from 'antd/es/typography';
import { lazy, Suspense, useEffect } from 'react';
import { Navigate, Route, Routes, useLocation, useNavigate } from 'react-router-dom';

import { setThemeMode } from './store/configSlice';
import { useAppDispatch, useAppSelector } from './store';

const { Header, Content, Sider } = Layout;

const HomePage = lazy(() => import('./pages/HomePage'));
const KLinePage = lazy(() => import('./pages/KLinePage'));
const BacktestPage = lazy(() => import('./pages/BacktestPage'));

const topNavItems = [
  { key: 'market', label: 'Market', to: '/kline' },
  { key: 'trade', label: 'Trade' },
  { key: 'positions', label: 'Positions' },
  { key: 'history', label: 'History' },
  { key: 'wallet', label: 'Wallet' },
  { key: 'orders', label: 'Orders' },
  { key: 'account', label: 'Account' },
];

const sideNavItems = [
  { key: '/kline', label: 'Main Terminal', icon: <LineChartOutlined /> },
  { key: '/', label: 'Dashboard', icon: <HomeOutlined /> },
  { key: '/backtest', label: 'Backtest Lab', icon: <ExperimentOutlined /> },
  { key: 'trade', label: 'Trade Desk', icon: <SwapOutlined /> },
  { key: 'signals', label: 'Signal Hub', icon: <ThunderboltOutlined /> },
  { key: 'portfolio', label: 'Portfolio', icon: <WalletOutlined /> },
];

export default function App() {
  const dispatch = useAppDispatch();
  const location = useLocation();
  const navigate = useNavigate();
  const language = useAppSelector((state) => state.config.language);
  const themeMode = useAppSelector((state) => state.config.themeMode);

  useEffect(() => {
    document.documentElement.lang = language;
  }, [language]);

  const activeTopKey =
    topNavItems.find((item) => item.to && item.to === location.pathname)?.key ?? '';
  const isSideItemActive = (key: string) => key === location.pathname;
  const nextThemeMode = themeMode === 'dark' ? 'light' : 'dark';
  const themeToggleLabel = `Switch to ${nextThemeMode} mode`;

  return (
    <Layout className="app-layout">
      <Header className="app-header">
        <div className="app-brand-block">
          <span className="app-brand-mark">
            <AppstoreOutlined />
          </span>
          <div>
            <Typography.Title className="app-brand" level={4}>
              量化研究平台
            </Typography.Title>
            <Typography.Text className="app-brand-subtitle">Skyline Digital</Typography.Text>
          </div>
        </div>

        <nav aria-label="Primary" className="app-top-nav">
          {topNavItems.map((item) => (
            <button
              aria-disabled={!item.to}
              className={item.key === activeTopKey ? 'app-top-nav__item is-active' : 'app-top-nav__item'}
              disabled={!item.to}
              key={item.key}
              onClick={() => item.to && navigate(item.to)}
              type="button"
            >
              {item.label}
            </button>
          ))}
        </nav>

        <div className="app-header-tools">
          <Tooltip title="Notifications">
            <Button aria-label="Notifications" icon={<BellOutlined />} shape="circle" type="text" />
          </Tooltip>
          <Tooltip title={themeToggleLabel}>
            <Button
              aria-label={themeToggleLabel}
              aria-pressed={themeMode === 'dark'}
              className="is-on"
              icon={themeMode === 'dark' ? <SunOutlined /> : <MoonOutlined />}
              onClick={() => dispatch(setThemeMode(nextThemeMode))}
              shape="circle"
              type="text"
            />
          </Tooltip>
          <Tooltip title="Settings">
            <Button aria-label="Settings" icon={<SettingOutlined />} shape="circle" type="text" />
          </Tooltip>
          <Avatar className="app-avatar" icon={<UserOutlined />} />
        </div>
      </Header>
      <Layout className="app-main-layout">
        <Sider className="app-sider" width={252}>
          <div className="terminal-card">
            <Typography.Text className="terminal-card__eyebrow">Workspace</Typography.Text>
            <Typography.Title className="terminal-card__title" level={4}>
              Main Terminal
            </Typography.Title>
          </div>

          <nav aria-label="Workspace" className="app-side-nav">
            {sideNavItems.map((item) => (
              <button
                aria-disabled={!item.key.startsWith('/')}
                className={isSideItemActive(item.key) ? 'app-side-nav__item is-active' : 'app-side-nav__item'}
                disabled={!item.key.startsWith('/')}
                key={item.key}
                onClick={() => item.key.startsWith('/') && navigate(item.key)}
                type="button"
              >
                <span className="app-side-nav__icon">{item.icon}</span>
                <span>{item.label}</span>
              </button>
            ))}
          </nav>

          <Button block className="deposit-button" icon={<WalletOutlined />} type="primary">
            Deposit Funds
          </Button>
        </Sider>

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
    </Layout>
  );
}
