/**
 * Token Manager
 *
 * RTR (Refresh Token Rotation) + Request Deduplication
 * - 토큰 갱신 중 다른 요청은 대기열에 추가
 * - 갱신 완료 시 대기 요청 일괄 재시도
 * - 무한 루프 방지
 */

import api from './api'
import { showError } from './errors'

// 상태 관리
let isRefreshing = false
let refreshSubscribers = []
let refreshAttempts = 0
const MAX_REFRESH_ATTEMPTS = 3

/**
 * 토큰 갱신 완료 대기 등록
 */
function subscribeTokenRefresh(callback) {
  refreshSubscribers.push(callback)
}

/**
 * 대기 중인 요청들에게 새 토큰 전달
 */
function onRefreshed(newToken) {
  refreshSubscribers.forEach((callback) => callback(newToken))
  refreshSubscribers = []
}

/**
 * 대기 중인 요청들에게 실패 알림
 */
function onRefreshFailed(error) {
  refreshSubscribers.forEach((callback) => callback(null, error))
  refreshSubscribers = []
}

/**
 * 토큰 갱신 (RTR)
 *
 * @returns {Promise<string|null>} 새 access_token 또는 null (실패 시)
 */
export async function refreshToken() {
  // 이미 갱신 중이면 대기
  if (isRefreshing) {
    return new Promise((resolve, reject) => {
      subscribeTokenRefresh((token, error) => {
        if (error) reject(error)
        else resolve(token)
      })
    })
  }

  // 무한 루프 방지
  if (refreshAttempts >= MAX_REFRESH_ATTEMPTS) {
    console.error('Token refresh max attempts exceeded')
    handleLogout('세션이 만료되었습니다. 다시 로그인해주세요.')
    return null
  }

  isRefreshing = true
  refreshAttempts++

  try {
    // POST /api/v1/auth/refresh (쿠키의 refresh_token 자동 전송)
    const { data } = await api.post('/api/v1/auth/refresh')

    // 새 access_token 저장
    const newToken = data.access_token
    localStorage.setItem('access_token', newToken)

    // 대기 중인 요청들에게 새 토큰 전달
    onRefreshed(newToken)

    // 성공 시 카운터 리셋
    refreshAttempts = 0

    return newToken
  } catch (error) {
    const status = error.response?.status
    const errorCode = error.response?.data?.detail?.error

    // 탈취 감지 (403 token_compromised)
    if (status === 403 && errorCode === 'token_compromised') {
      handleLogout('보안을 위해 로그아웃되었습니다. 다시 로그인해주세요.')
    }
    // 토큰 만료/무효 (401)
    else if (status === 401) {
      handleLogout('세션이 만료되었습니다. 다시 로그인해주세요.')
    }
    // 기타 에러
    else {
      console.error('Token refresh failed:', error)
    }

    onRefreshFailed(error)
    return null
  } finally {
    isRefreshing = false
  }
}

/**
 * 로그아웃 처리
 */
function handleLogout(message) {
  localStorage.removeItem('access_token')
  refreshAttempts = 0

  if (message) {
    showError(message)
  }

  // 로그인 페이지가 아닐 때만 리다이렉트
  if (!window.location.pathname.includes('/login')) {
    setTimeout(() => {
      window.location.href = '/login'
    }, 1500)
  }
}

/**
 * 현재 갱신 중인지 확인
 */
export function isTokenRefreshing() {
  return isRefreshing
}

/**
 * 갱신 시도 횟수 리셋 (로그인 성공 시 호출)
 */
export function resetRefreshAttempts() {
  refreshAttempts = 0
}
