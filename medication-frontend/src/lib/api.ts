/**
 * API 클라이언트 (TypeScript 버전)
 */

import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';
import { config } from '@/config/env';
import { parseApiError, ERROR_CODE_MESSAGES, HTTP_STATUS_MESSAGES } from './errors';

// Axios 에러 객체에 파싱된 정보를 담기 위한 타입 확장
export interface ParsedApiError {
  code: string;
  message: string;
  status: number;
  original: any;
}

export interface ApiError extends AxiosError {
  parsed?: ParsedApiError;
}

const api = axios.create({
  baseURL: config.API_BASE_URL,
  withCredentials: true,
  timeout: 10000,
});

api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => config,
  (error: any) => Promise.reject(error)
);

// 응답 인터셉터: 에러 처리 + RTR
api.interceptors.response.use(
  (response) => response,
  async (error: ApiError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };
    const status = error.response?.status;

    // 401 Unauthorized - 토큰 갱신 시도
    if (status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      // /auth/refresh 요청 자체가 401이면 바로 로그아웃
      if (originalRequest.url?.includes('/auth/refresh')) {
        return Promise.reject(error);
      }

      try {
        // 동적 import로 순환 참조 방지
        const { refreshToken } = await import('./tokenManager');
        const refreshed = await refreshToken();

        if (refreshed) {
          // 쿠키가 갱신되었으므로 원래 요청 재시도
          return api.request(originalRequest);
        }
      } catch (refreshError) {
        return Promise.reject(refreshError);
      }
    }

    // 에러 객체에 파싱된 정보 첨부
    const parsed = parseApiError(error);
    error.parsed = parsed;

    return Promise.reject(error);
  }
);

export default api;

// 에러 관련 유틸 re-export
export { parseApiError, ERROR_CODE_MESSAGES, HTTP_STATUS_MESSAGES } from './errors';
export { handleApiError, showError } from './errors';
