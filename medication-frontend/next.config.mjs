/** @type {import('next').NextConfig} */
const nextConfig = {
  // 이미지 최적화 설정
  images: {
    remotePatterns: [],
    unoptimized: false,
  },

  // 🚀 API 프록시 설정 추가
  async rewrites() {
    return [
      {
        // 프론트엔드(localhost:3000)에서 /api/v1/... 으로 요청을 보내면
        source: '/api/v1/:path*',

        // package.json의 dotenv가 읽어온 ../.env 의 주소로 몰래 전달해 줍니다!
        // (만약 env에 값이 없다면 기본값인 로컬 8000번 포트로 보냅니다)
        destination: `${process.env.API_BASE_URL || 'http://localhost:8000'}/api/v1/:path*`,
      },
    ];
  },
}

export default nextConfig