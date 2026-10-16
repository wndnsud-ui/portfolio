import axios, { AxiosError } from 'axios';
import { getToken, useAuth } from '../hooks/useAuth';

export const api = axios.create({
  baseURL: (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? 'http://localhost:8000',
  timeout: 60_000,
});

api.interceptors.request.use((config) => {
  const token = getToken();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (r) => r,
  (err: AxiosError) => {
    if (err.response?.status === 401) void useAuth.getState().signOut();
    return Promise.reject(err);
  },
);

/** 서버 오류 응답에서 화면에 보여줄 한국어 메시지를 꺼낸다. */
export function errorMessage(err: unknown, fallback = '잠시 후 다시 시도해 주세요.'): string {
  if (axios.isAxiosError(err)) {
    const detail = (err.response?.data as { detail?: unknown } | undefined)?.detail;
    if (typeof detail === 'string') return detail;
    if (detail && typeof detail === 'object' && 'message' in detail) return String((detail as { message: string }).message);
    if (!err.response) return '서버에 연결할 수 없어요. 네트워크를 확인해 주세요.';
  }
  if (err instanceof Error && err.message) return err.message;
  return fallback;
}
