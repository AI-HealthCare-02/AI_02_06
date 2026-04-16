/**
 * 환경별 설정 (JavaScript 복구 버전)
 */

const ENV = process.env.NEXT_PUBLIC_ENV || 'local';

// 환경별 기본값
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
};

const currentConfig = ENV_CONFIG[ENV] || ENV_CONFIG.local;

export const config = {
  ENV,
  API_BASE_URL: process.env.NEXT_PUBLIC_API_BASE_URL ?? currentConfig.API_BASE_URL ?? '',
  KAKAO_CLIENT_ID: process.env.NEXT_PUBLIC_KAKAO_CLIENT_ID || '',
  KAKAO_REDIRECT_URI: process.env.NEXT_PUBLIC_KAKAO_REDIRECT_URI || currentConfig.KAKAO_REDIRECT_URI || '',
};

export default config;
