/** @type {import('next').NextConfig} */
const nextConfig = {
  // 이미지 최적화 설정
  images: {
    remotePatterns: [],
    unoptimized: false,
  },

  // API 프록시 경로에서 trailing slash 리다이렉트 방지
  skipTrailingSlashRedirect: true,

  // 🚀 API 프록시 설정 (백엔드로 프록시)
  async rewrites() {
    const apiBaseUrl = process.env.API_BASE_URL || 'http://localhost:8000'
    return [
      {
        // /api/* 모든 요청을 백엔드로 프록시 (trailing slash 포함)
        source: '/api/:path*',
        destination: `${apiBaseUrl}/api/:path*`,
      },
    ];
  },
}

export default nextConfig