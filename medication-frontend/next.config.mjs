/** @type {import('next').NextConfig} */
const nextConfig = {
  images: {
    // 외부 이미지 도메인 허용 (필요시 추가)
    remotePatterns: [
      // 예시: 외부 이미지 서버가 있다면 추가
      // {
      //   protocol: 'https',
      //   hostname: 'example.com',
      //   port: '',
      //   pathname: '/images/**',
      // },
    ],
    // 이미지 최적화 활성화 (성능 향상)
    unoptimized: false,
    // 이미지 품질 설정 (1-100, 기본값: 75)
    quality: 85,
    // 허용할 이미지 크기들
    deviceSizes: [640, 750, 828, 1080, 1200, 1920, 2048, 3840],
    imageSizes: [16, 32, 48, 64, 96, 128, 256, 384],
  },

  // trailing slash 자동 리다이렉트 비활성화 (API 프록시 호환)
  skipTrailingSlashRedirect: true,

  // API 프록시: /api/* -> 백엔드 서버
  // - local/dev: http://localhost:8000
  // - prod: Vercel 환경변수 API_BASE_URL
  async rewrites() {
    const apiBaseUrl = process.env.API_BASE_URL || 'http://localhost:8000'
    return [
      {
        source: '/api/:path*',
        destination: `${apiBaseUrl}/api/:path*`,
      },
    ]
  },
}

export default nextConfig
