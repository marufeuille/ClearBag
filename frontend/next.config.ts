import type { NextConfig } from "next";
import withPWA from "next-pwa";

const pwaConfig = withPWA({
  dest: "public",
  disable: process.env.NODE_ENV === "development",
  register: true,
  skipWaiting: true,
  customWorkerDir: "worker",
});

const nextConfig: NextConfig = {
  // Firebase Hosting への静的エクスポート
  output: "export",
  trailingSlash: true,
  images: {
    unoptimized: true, // static export では Image Optimization が使えない
  },
};

export default pwaConfig(nextConfig);
