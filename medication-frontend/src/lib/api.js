/**
 * API 클라이언트 설정
 *
 * axios 인스턴스 생성 및 인터셉터 설정
 */

import axios from 'axios'
import { parseApiError, ERROR_CODE_MESSAGES, HTTP_STATUS_MESSAGES } from './errors'

// 모든 API 요청의 기본 설정
const api = axios.create({
  baseURL: 'http://localhost:8000',
  withCredentials: true,  // 쿠키 자동 포함 (refresh_token용)
  timeout: 10000,         // 10초 타임아웃
})

// 요청 인터셉터: access_token 자동 첨부
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// 응답 인터셉터: 에러 처리
api.interceptors.response.use(
  // 성공 응답은 그대로 반환
  (response) => response,

  // 에러 응답 처리
  (error) => {
    const parsed = parseApiError(error)

    // 401 Unauthorized - 토큰 만료/무효
    if (parsed.status === 401) {
      localStorage.removeItem('access_token')
      // 로그인 페이지가 아닐 때만 리다이렉트
      if (!window.location.pathname.includes('/login')) {
        window.location.href = '/login'
      }
    }

    // 에러 객체에 파싱된 정보 첨부
    error.parsed = parsed

    return Promise.reject(error)
  }
)

export default api

// 에러 관련 유틸 re-export
export { parseApiError, ERROR_CODE_MESSAGES, HTTP_STATUS_MESSAGES } from './errors'
export { handleApiError, showError } from './errors'