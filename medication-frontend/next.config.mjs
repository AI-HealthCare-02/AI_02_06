/** @type {import('next').NextConfig} */
const nextConfig = {
  // Static Export: Nginx가 out/ 폴더를 정적 파일로 서빙
  output: 'export',
  // 이미지 최적화 설정 (Static Export에서는 unoptimized: true 필수)
  images: {
    remotePatterns: [],
    unoptimized: true,
  },
}

export default nextConfig
