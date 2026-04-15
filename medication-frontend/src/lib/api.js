/**
 * API 클라이언트
 *
 * - Next.js rewrites 프록시 사용 (baseURL='')
 * - HttpOnly 쿠키 기반 인증
 * - RTR (Refresh Token Rotation) 지원
 */

import axios from 'axios'
import { config } from '@/config/env'
import { parseApiError, ERROR_CODE_MESSAGES, HTTP_STATUS_MESSAGES } from './errors'

const api = axios.create({
  baseURL: config.API_BASE_URL,
  withCredentials: true,
  timeout: 10000,
})

api.interceptors.request.use(
  (config) => config,
  (error) => Promise.reject(error)
)

// 응답 인터셉터: 에러 처리 + RTR
api.interceptors.response.use(
  // 성공 응답은 그대로 반환
  (response) => response,

  // 에러 응답 처리
  async (error) => {
    const originalRequest = error.config
    const status = error.response?.status

    // 401 Unauthorized - 토큰 갱신 시도
    if (status === 401 && !originalRequest._retry) {
      originalRequest._retry = true

      // /auth/refresh 요청 자체가 401이면 바로 로그아웃
      if (originalRequest.url?.includes('/auth/refresh')) {
        return Promise.reject(error)
      }

      try {
        // 동적 import로 순환 참조 방지
        const { refreshToken } = await import('./tokenManager')
        const refreshed = await refreshToken()

        if (refreshed) {
          // 쿠키가 갱신되었으므로 원래 요청 재시도
          // (access_token 쿠키가 자동으로 전송됨)
          return api.request(originalRequest)
        }
      } catch (refreshError) {
        // 갱신 실패 - tokenManager에서 로그아웃 처리됨
        return Promise.reject(refreshError)
      }
    }

    // 에러 객체에 파싱된 정보 첨부
    const parsed = parseApiError(error)
    error.parsed = parsed

    return Promise.reject(error)
  }
)

export default api

// 에러 관련 유틸 re-export
export { parseApiError, ERROR_CODE_MESSAGES, HTTP_STATUS_MESSAGES } from './errors'
export { handleApiError, showError } from './errors'