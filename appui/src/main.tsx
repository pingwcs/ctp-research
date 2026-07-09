import React from 'react';
import ReactDOM from 'react-dom/client';
import ConfigProvider from 'antd/es/config-provider';
import 'antd/dist/reset.css';
import { Provider } from 'react-redux';
import { BrowserRouter } from 'react-router-dom';

import App from './App';
import { installResponsiveRootFont } from './config/responsive';
import { getAntTheme } from './config/theme';
import { store, useAppSelector } from './store';
import './styles/index.scss';

installResponsiveRootFont();

function ThemedApp() {
  const themeMode = useAppSelector((state) => state.config.themeMode);
  const theme = React.useMemo(() => getAntTheme(themeMode), [themeMode]);

  React.useEffect(() => {
    document.documentElement.dataset.theme = themeMode;
  }, [themeMode]);

  return (
    <ConfigProvider theme={theme}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </ConfigProvider>
  );
}

ReactDOM.createRoot(document.getElementById('root') as HTMLElement).render(
  <React.StrictMode>
    <Provider store={store}>
      <ThemedApp />
    </Provider>
  </React.StrictMode>,
);
