/** @type {import('next').NextConfig} */
const nextConfig = {
  // Docker 프로덕션 빌드용 standalone 출력
  output: "standalone",

  // API 요청을 FastAPI로 프록시
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: process.env.API_URL
          ? `${process.env.API_URL}/api/:path*`
          : "http://localhost:8000/api/:path*",
      },
    ];
  },
};

export default nextConfig;
