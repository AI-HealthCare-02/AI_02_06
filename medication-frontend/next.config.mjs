/** @type {import('next').NextConfig} */
const nextConfig = {
  // Vercel 배포 시 SSR 사용 (output: "export" 제거)
  // 로컬에서 Static Export가 필요하면: npm run build:static

  // 이미지 최적화 설정
  images: {
    // 외부 이미지 도메인 허용 (필요시 추가)
    remotePatterns: [],
    // Vercel에서는 Image Optimization 사용 가능
    unoptimized: false,
  },

  // 환경 변수 (클라이언트 노출용은 NEXT_PUBLIC_ 접두사 필요)
  env: {
    NEXT_PUBLIC_API_BASE_URL: process.env.NEXT_PUBLIC_API_BASE_URL,
  },
};

export default nextConfig;
