import type { NextConfig } from "next";
import withPWA from "next-pwa";

const defaultRuntimeCaching = require("next-pwa/cache");
const runtimeCaching = defaultRuntimeCaching.filter(
  (entry: { options?: { cacheName?: string } }) =>
    entry?.options?.cacheName !== "cross-origin"
);

const pwaConfig = withPWA({
  dest: "public",
  disable: process.env.NODE_ENV === "development",
  register: false,
  skipWaiting: true,
  customWorkerDir: "worker",
  runtimeCaching,
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
