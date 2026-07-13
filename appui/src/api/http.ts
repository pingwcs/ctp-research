import axios, {
  AxiosError,
  AxiosHeaders,
  type AxiosInstance,
  type AxiosRequestConfig,
} from 'axios';

const API_TIMEOUT_MS = 15000;
let bearerToken: string | null = null;

interface ApiErrorPayload {
  detail?: string | { msg?: string }[];
  message?: string;
}

export function setHttpAuthToken(token: string | null) {
  bearerToken = token;
}

function getErrorMessage(error: unknown) {
  if (!axios.isAxiosError(error)) {
    return error instanceof Error ? error.message : 'Unexpected request error';
  }

  const axiosError = error as AxiosError<ApiErrorPayload>;
  const payload = axiosError.response?.data;
  if (typeof payload?.detail === 'string') {
    return payload.detail;
  }
  if (Array.isArray(payload?.detail)) {
    return payload.detail.map((item) => item.msg).filter(Boolean).join('; ') || 'Request validation failed';
  }
  return payload?.message || axiosError.message || 'API request failed';
}

function createHttpClient(instance: AxiosInstance) {
  return {
    async get<T>(url: string, config?: AxiosRequestConfig) {
      try {
        const response = await instance.get<T>(url, config);
        return response.data;
      } catch (error) {
        throw new Error(getErrorMessage(error));
      }
    },
    async post<T, TBody = unknown>(url: string, data?: TBody, config?: AxiosRequestConfig) {
      try {
        const response = await instance.post<T>(url, data, config);
        return response.data;
      } catch (error) {
        throw new Error(getErrorMessage(error));
      }
    },
    async put<T, TBody = unknown>(url: string, data?: TBody, config?: AxiosRequestConfig) {
      try {
        const response = await instance.put<T>(url, data, config);
        return response.data;
      } catch (error) {
        throw new Error(getErrorMessage(error));
      }
    },
    async patch<T, TBody = unknown>(url: string, data?: TBody, config?: AxiosRequestConfig) {
      try {
        const response = await instance.patch<T>(url, data, config);
        return response.data;
      } catch (error) {
        throw new Error(getErrorMessage(error));
      }
    },
    async delete<T>(url: string, config?: AxiosRequestConfig) {
      try {
        const response = await instance.delete<T>(url, config);
        return response.data;
      } catch (error) {
        throw new Error(getErrorMessage(error));
      }
    },
  };
}

export const http = createHttpClient(
  (() => {
    const instance = axios.create({
      timeout: API_TIMEOUT_MS,
    });
    instance.interceptors.request.use((config) => {
      if (bearerToken) {
        const headers = AxiosHeaders.from(config.headers);
        headers.set('Authorization', `Bearer ${bearerToken}`);
        config.headers = headers;
      }
      return config;
    });
    return instance;
  })(),
);
