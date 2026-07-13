import LockOutlined from '@ant-design/icons/LockOutlined';
import LoginOutlined from '@ant-design/icons/LoginOutlined';
import MailOutlined from '@ant-design/icons/MailOutlined';
import UserAddOutlined from '@ant-design/icons/UserAddOutlined';
import Alert from 'antd/es/alert';
import Button from 'antd/es/button';
import Form from 'antd/es/form';
import Input from 'antd/es/input';
import Segmented from 'antd/es/segmented';
import Space from 'antd/es/space';
import Typography from 'antd/es/typography';
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { clearAuthError, loginWithEmail, registerWithEmail } from '../store/authSlice';
import { useAppDispatch, useAppSelector } from '../store';

type AuthMode = 'login' | 'register';

interface AuthFormValues {
  email: string;
  password: string;
}

export default function AuthPage() {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const [form] = Form.useForm<AuthFormValues>();
  const [mode, setMode] = useState<AuthMode>('login');
  const { error, status, user } = useAppSelector((state) => state.auth);
  const loading = status === 'loading';

  useEffect(() => {
    if (user) {
      navigate('/', { replace: true });
    }
  }, [navigate, user]);

  const handleModeChange = (value: string | number) => {
    setMode(value as AuthMode);
    dispatch(clearAuthError());
  };

  const handleSubmit = async (values: AuthFormValues) => {
    const credentials = {
      email: values.email.trim(),
      password: values.password,
    };
    const result =
      mode === 'login'
        ? await dispatch(loginWithEmail(credentials))
        : await dispatch(registerWithEmail(credentials));

    if (loginWithEmail.fulfilled.match(result) || registerWithEmail.fulfilled.match(result)) {
      navigate('/', { replace: true });
    }
  };

  return (
    <main className="auth-page">
      <section className="auth-panel" aria-label="Authentication">
        <div className="auth-panel__brand">
          <span className="auth-panel__mark">
            {mode === 'login' ? <LoginOutlined /> : <UserAddOutlined />}
          </span>
          <div>
            <Typography.Title level={2}>Quant Workspace</Typography.Title>
            <Typography.Text type="secondary">
              {mode === 'login' ? 'Sign in' : 'Create account'}
            </Typography.Text>
          </div>
        </div>

        <Segmented
          block
          className="auth-mode"
          onChange={handleModeChange}
          options={[
            { label: 'Login', value: 'login' },
            { label: 'Register', value: 'register' },
          ]}
          value={mode}
        />

        {error ? <Alert message={error} showIcon type="error" /> : null}

        <Form<AuthFormValues>
          autoComplete={mode === 'login' ? 'on' : 'off'}
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
          requiredMark={false}
        >
          <Form.Item
            label="Email"
            name="email"
            rules={[
              { required: true, message: 'Email is required' },
              { type: 'email', message: 'Enter a valid email' },
            ]}
          >
            <Input
              autoComplete="email"
              disabled={loading}
              inputMode="email"
              prefix={<MailOutlined />}
            />
          </Form.Item>

          <Form.Item
            label="Password"
            name="password"
            rules={[
              { required: true, message: 'Password is required' },
              { min: 8, message: 'Use at least 8 characters' },
            ]}
          >
            <Input.Password
              autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
              disabled={loading}
              prefix={<LockOutlined />}
            />
          </Form.Item>

          <Space className="auth-actions" direction="vertical" size={12}>
            <Button
              block
              htmlType="submit"
              icon={mode === 'login' ? <LoginOutlined /> : <UserAddOutlined />}
              loading={loading}
              type="primary"
            >
              {mode === 'login' ? 'Login' : 'Register'}
            </Button>
          </Space>
        </Form>
      </section>
    </main>
  );
}
