/**
 * Token Manager (TypeScript 버전)
 *
 * RTR (Refresh Token Rotation) + Request Deduplication
 */

import api from './api';
import { showError } from './errors';

// 상태 관리
let isRefreshing = false;
let refreshSubscribers: ((token: any, error?: any) => void)[] = [];
let refreshAttempts = 0;
const MAX_REFRESH_ATTEMPTS = 3;

/**
 * 토큰 갱신 완료 대기 등록
 */
function subscribeTokenRefresh(callback: (token: any, error?: any) => void) {
  refreshSubscribers.push(callback);
}

/**
 * 대기 중인 요청들에게 새 토큰 전달
 */
function onRefreshed(newToken: any) {
  refreshSubscribers.forEach((callback) => callback(newToken));
  refreshSubscribers = [];
}

/**
 * 대기 중인 요청들에게 실패 알림
 */
function onRefreshFailed(error: any) {
  refreshSubscribers.forEach((callback) => callback(null, error));
  refreshSubscribers = [];
}

/**
 * 토큰 갱신 (RTR)
 */
export async function refreshToken(): Promise<boolean | null> {
  // 이미 갱신 중이면 대기
  if (isRefreshing) {
    return new Promise((resolve, reject) => {
      subscribeTokenRefresh((token, error) => {
        if (error) reject(error);
        else resolve(token);
      });
    });
  }

  // 무한 루프 방지
  if (refreshAttempts >= MAX_REFRESH_ATTEMPTS) {
    console.error('Token refresh max attempts exceeded');
    handleLogout('세션이 만료되었습니다. 다시 로그인해주세요.');
    return null;
  }

  isRefreshing = true;
  refreshAttempts++;

  try {
    // POST /api/v1/auth/refresh (쿠키 자동 전송/수신)
    await api.post('/api/v1/auth/refresh');

    // 대기 중인 요청들에게 갱신 완료 알림
    onRefreshed(true);

    // 성공 시 카운터 리셋
    refreshAttempts = 0;

    return true;
  } catch (error: any) {
    const status = error.response?.status;
    const errorCode = error.response?.data?.detail?.error;

    // 탈취 감지 (403 token_compromised)
    if (status === 403 && errorCode === 'token_compromised') {
      handleLogout('보안을 위해 로그아웃되었습니다. 다시 로그인해주세요.');
    }
    // 토큰 만료/무효 (401)
    else if (status === 401) {
      handleLogout('세션이 만료되었습니다. 다시 로그인해주세요.');
    } else {
      console.error('Token refresh failed:', error);
    }

    onRefreshFailed(error);
    return null;
  } finally {
    isRefreshing = false;
  }
}

/**
 * 로그아웃 처리
 */
export async function handleLogout(message?: string) {
  refreshAttempts = 0;

  try {
    await api.post('/api/v1/auth/logout');
  } catch {
    // 무시
  }

  if (message) {
    showError(message);
  }

  if (typeof window !== 'undefined' && !window.location.pathname.includes('/login')) {
    setTimeout(() => {
      window.location.href = '/login';
    }, 1500);
  }
}

/**
 * 현재 갱신 중인지 확인
 */
export function isTokenRefreshing(): boolean {
  return isRefreshing;
}

/**
 * 갱신 시도 횟수 리셋
 */
export function resetRefreshAttempts(): void {
  refreshAttempts = 0;
}
