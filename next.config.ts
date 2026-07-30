import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  experimental: {
    serverActions: {
      bodySizeLimit: 25 * 1024 * 1024,
    },
  },
};

export default nextConfig;
