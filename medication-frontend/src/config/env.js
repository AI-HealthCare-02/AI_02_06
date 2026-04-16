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

// API URL에서 후행 슬래시 자동 제거
const cleanApiUrl = (url) => {
  if (!url) return '';
  return url.replace(/\/$/, '');
};

// 보안 유틸리티
export const securityUtils = {
  shouldShowDevLogin: () => {
    // 다중 레이어 보안 검증
    const envCheck = process.env.NEXT_PUBLIC_ENV === 'local';
    const flagCheck = process.env.NEXT_PUBLIC_ENABLE_DEV_LOGIN === 'true';
    const runtimeCheck = ENV === 'local';

    return envCheck && flagCheck && runtimeCheck;
  },

  detectEnvironmentTampering: () => {
    const clientEnv = process.env.NEXT_PUBLIC_ENV;
    const runtimeEnv = ENV;

    if (clientEnv !== runtimeEnv) {
      console.warn('Environment tampering detected');
      return true;
    }
    return false;
  }
};

export const config = {
  ENV,
  API_BASE_URL: cleanApiUrl(process.env.NEXT_PUBLIC_API_BASE_URL ?? currentConfig.API_BASE_URL),
  KAKAO_CLIENT_ID: process.env.NEXT_PUBLIC_KAKAO_CLIENT_ID || '',
  KAKAO_REDIRECT_URI: process.env.NEXT_PUBLIC_KAKAO_REDIRECT_URI || currentConfig.KAKAO_REDIRECT_URI || '',

  // 보안 설정
  ENABLE_DEV_LOGIN: ENV !== 'prod' && process.env.NEXT_PUBLIC_ENABLE_DEV_LOGIN === 'true'
};

export default config;
