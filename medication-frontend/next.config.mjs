/** @type {import('next').NextConfig} */
const nextConfig = {
  // Docker 프로덕션 빌드용 standalone 출력
  output: "standalone",

  // API 요청을 FastAPI로 프록시 (서버 사이드)
  // - Docker 환경: API_URL=http://fastapi:8000 (docker-compose에서 설정)
  // - 로컬 개발: http://localhost:8000 (기본값)
  async rewrites() {
    const apiUrl = process.env.API_URL || "http://localhost:8000";
    console.log(`[Next.js] API rewrites destination: ${apiUrl}`);

    return [
      {
        source: "/api/:path*",
        destination: `${apiUrl}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
