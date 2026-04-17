/**
 * Auth Manager (인증 관리자)
 * 인증 상태 관리, 토큰 갱신, 로그아웃 처리
 */

import api from './api';
import { showError } from './errors';

let isRefreshing = false;
let refreshSubscribers = [];
let refreshAttempts = 0;
const MAX_REFRESH_ATTEMPTS = 3;

function subscribeTokenRefresh(callback) {
  refreshSubscribers.push(callback);
}

function onRefreshed(newToken) {
  refreshSubscribers.forEach((callback) => callback(newToken));
  refreshSubscribers = [];
}

function onRefreshFailed(error) {
  refreshSubscribers.forEach((callback) => callback(null, error));
  refreshSubscribers = [];
}

export async function refreshToken() {
  if (isRefreshing) {
    return new Promise((resolve, reject) => {
      subscribeTokenRefresh((token, error) => {
        if (error) reject(error);
        else resolve(token);
      });
    });
  }

  if (refreshAttempts >= MAX_REFRESH_ATTEMPTS) {
    console.error('Token refresh max attempts exceeded');
    handleLogout('로그아웃 되었습니다.');
    return null;
  }

  isRefreshing = true;
  refreshAttempts++;

  try {
    await api.post('/api/v1/auth/refresh');
    onRefreshed(true);
    refreshAttempts = 0;
    return true;
  } catch (error) {
    const status = error.response?.status;
    const errorCode = error.response?.data?.detail?.error;

    if (status === 403 && errorCode === 'token_compromised') {
      handleLogout('보안을 위해 로그아웃 되었습니다.');
    } else if (status === 401) {
      handleLogout('로그아웃 되었습니다.');
    } else {
      console.error('Token refresh failed:', error);
    }

    onRefreshFailed(error);
    return null;
  } finally {
    isRefreshing = false;
  }
}

export async function handleLogout(message) {
  refreshAttempts = 0;
  try {
    await api.post('/api/v1/auth/logout');
  } catch {
    // 무시
  }

  if (message) {
    showError(message);
  }

  // AuthGuard가 이미 리다이렉트를 처리하므로 지연 제거
  if (typeof window !== 'undefined' && !window.location.pathname.includes('/login')) {
    window.location.href = '/login';
  }
}

export function isTokenRefreshing() {
  return isRefreshing;
}

export function resetRefreshAttempts() {
  refreshAttempts = 0;
}
