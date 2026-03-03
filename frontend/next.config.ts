import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // output: 'export',
  images: {
    unoptimized: true,
  },
  // 프론트에서 /api로 쏘는 요청을 가로채서 백엔드 주소로 프록시(우회) 전달합니다.
  async rewrites() {
    return [
      {
        source: "/api/:path*", // 브라우저가 호출하는 가짜 경로
        destination: `${process.env.BACKEND_API_URL || "http://localhost:8000"}/api/:path*`, // 실제 API 목적지
      },
    ];
  },
};

export default nextConfig;
