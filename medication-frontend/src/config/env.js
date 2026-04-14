/**
 * 환경별 설정
 *
 * NEXT_PUBLIC_ENV 값에 따라 자동으로 URL이 설정됩니다.
 * - local: 로컬 개발 환경 (localhost)
 * - prod: 프로덕션 환경 (EC2 + Vercel)
 */

const ENV = process.env.NEXT_PUBLIC_ENV || 'local'

// 환경별 URL 설정
const ENV_CONFIG = {
  local: {
    API_BASE_URL: 'http://localhost:8000',
    KAKAO_REDIRECT_URI: 'http://localhost:3000/auth/kakao/callback',
  },
  dev: {
    // Dev 환경: EC2 백엔드 + Vercel Preview
    API_BASE_URL: 'http://52.78.62.12',
    KAKAO_REDIRECT_URI: 'https://ai-02-06.vercel.app/auth/kakao/callback',
  },
  prod: {
    // Prod 환경: EC2 백엔드 + Vercel Production
    API_BASE_URL: 'http://52.78.62.12',
    KAKAO_REDIRECT_URI: 'https://ai-02-06.vercel.app/auth/kakao/callback',
  },
}

// 현재 환경 설정 가져오기
const currentConfig = ENV_CONFIG[ENV] || ENV_CONFIG.local

// .env에서 개별 지정하면 우선, 아니면 환경별 기본값 사용
export const config = {
  ENV,
  API_BASE_URL: process.env.NEXT_PUBLIC_API_BASE_URL || currentConfig.API_BASE_URL,
  KAKAO_CLIENT_ID: process.env.NEXT_PUBLIC_KAKAO_CLIENT_ID || '',
  KAKAO_REDIRECT_URI: process.env.NEXT_PUBLIC_KAKAO_REDIRECT_URI || currentConfig.KAKAO_REDIRECT_URI,
}

export default config
