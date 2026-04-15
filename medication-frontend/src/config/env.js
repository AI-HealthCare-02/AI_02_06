/**
 * 환경별 설정
 *
 * NEXT_PUBLIC_ENV 값에 따라 자동으로 URL이 설정됩니다.
 *
 * - local: 로컬 Docker 환경 (dev 로그인 버튼 표시)
 * - dev: 로컬 Docker 환경 (dev 로그인 버튼 숨김, 카카오 테스트용)
 * - prod: EC2 + Vercel 배포 환경
 */

const ENV = process.env.NEXT_PUBLIC_ENV || 'local'

// 환경별 URL 설정
// local/dev: 동일한 로컬 Docker 환경
// prod: EC2 백엔드 + Vercel 프론트엔드
const ENV_CONFIG = {
  local: {
    API_BASE_URL: '',  // 로컬에서는 Nginx 프록시 사용 (/api/* -> fastapi:8000)
    KAKAO_REDIRECT_URI: 'http://localhost:3000/auth/kakao/callback',
  },
  dev: {
    API_BASE_URL: '',  // 로컬에서는 Nginx 프록시 사용
    KAKAO_REDIRECT_URI: 'http://localhost:3000/auth/kakao/callback',
  },
  prod: {
    // Prod: Next.js rewrites 프록시 사용 (서드파티 쿠키 문제 해결)
    // 실제 프록시 대상은 next.config.mjs의 API_BASE_URL 환경변수로 설정
    API_BASE_URL: '',
    KAKAO_REDIRECT_URI: 'https://ai-02-06.vercel.app/auth/kakao/callback',
  },
}

// 현재 환경 설정 가져오기
const currentConfig = ENV_CONFIG[ENV] || ENV_CONFIG.local

// .env에서 개별 지정하면 우선, 아니면 환경별 기본값 사용
export const config = {
  ENV,
  API_BASE_URL: process.env.NEXT_PUBLIC_API_BASE_URL ?? currentConfig.API_BASE_URL,
  KAKAO_CLIENT_ID: process.env.NEXT_PUBLIC_KAKAO_CLIENT_ID || '',
  KAKAO_REDIRECT_URI: process.env.NEXT_PUBLIC_KAKAO_REDIRECT_URI || currentConfig.KAKAO_REDIRECT_URI,
}

export default config
