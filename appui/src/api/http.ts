import axios, {
  AxiosError,
  type AxiosInstance,
  type AxiosRequestConfig,
} from 'axios';

import { API_TIMEOUT_MS } from '../config/api';

interface ApiErrorPayload {
  detail?: string;
  message?: string;
}

function getErrorMessage(error: unknown) {
  if (!axios.isAxiosError(error)) {
    return error instanceof Error ? error.message : 'Unexpected request error';
  }

  const axiosError = error as AxiosError<ApiErrorPayload>;
  const payload = axiosError.response?.data;
  return payload?.detail || payload?.message || axiosError.message || 'API request failed';
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

export const http = createHttpClient(axios.create({
  timeout: API_TIMEOUT_MS,
}));
