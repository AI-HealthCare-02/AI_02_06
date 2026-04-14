/** @type {import('next').NextConfig} */
const nextConfig = {
  // 이미지 최적화 설정
  images: {
    remotePatterns: [],
    unoptimized: false,
  },

  // API 프록시 설정 (Mixed Content 해결)
  // Vercel(HTTPS) -> EC2(HTTP) 요청을 프록시로 처리
  async rewrites() {
    const apiUrl = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'

    return [
      {
        source: '/api/:path*',
        destination: `${apiUrl}/api/:path*`,
      },
    ]
  },
}

export default nextConfig
