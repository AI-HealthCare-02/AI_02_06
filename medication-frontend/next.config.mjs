/** @type {import('next').NextConfig} */
const nextConfig = {
  images: {
    remotePatterns: [],
    unoptimized: false,
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