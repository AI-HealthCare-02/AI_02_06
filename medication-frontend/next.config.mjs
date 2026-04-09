/** @type {import('next').NextConfig} */
const nextConfig = {
  // Static Export - 정적 파일만 생성
  output: "export",

  // 정적 파일 경로에 trailing slash 추가 (Nginx 호환성)
  trailingSlash: true,

  // Static Export에서는 Next.js Image Optimization 사용 불가
  images: {
    unoptimized: true,
  },
};

export default nextConfig;
