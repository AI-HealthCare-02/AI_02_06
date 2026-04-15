/**
 * 환경별 설정
 *
 * NEXT_PUBLIC_ENV에 따라 환경 구분:
 * - local: 로컬 Docker (dev 로그인 버튼 O)
 * - dev: 로컬 Docker (카카오 로그인 테스트)
 * - prod: Vercel + EC2
 */

const ENV = process.env.NEXT_PUBLIC_ENV || 'local'

// 환경별 기본값
// API_BASE_URL은 모든 환경에서 빈 문자열 (Next.js rewrites 프록시 사용)
const ENV_CONFIG = {
  local: {
    API_BASE_URL: '',
    KAKAO_REDIRECT_URI: 'http://localhost:3000/auth/kakao/callback',
  },
  dev: {
    API_BASE_URL: '',
    KAKAO_REDIRECT_URI: 'http://localhost:3000/auth/kakao/callback',
  },
  prod: {
    API_BASE_URL: '',
    KAKAO_REDIRECT_URI: 'https://ai-02-06.vercel.app/auth/kakao/callback',
  },
}

const currentConfig = ENV_CONFIG[ENV] || ENV_CONFIG.local

// 환경변수 우선, 없으면 기본값 사용
export const config = {
  ENV,
  API_BASE_URL: process.env.NEXT_PUBLIC_API_BASE_URL ?? currentConfig.API_BASE_URL,
  KAKAO_CLIENT_ID: process.env.NEXT_PUBLIC_KAKAO_CLIENT_ID || '',
  KAKAO_REDIRECT_URI: process.env.NEXT_PUBLIC_KAKAO_REDIRECT_URI || currentConfig.KAKAO_REDIRECT_URI,
}

export default config
