import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // 배럴 패키지 임포트를 사용 항목만 deep-import 로 변환(dev 컴파일·번들 축소).
  experimental: {
    optimizePackageImports: ["lucide-react"],
  },
};

export default nextConfig;
