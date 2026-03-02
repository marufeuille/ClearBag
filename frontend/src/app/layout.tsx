import type { Metadata, Viewport } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import ServiceWorkerRegistrar from "@/components/ServiceWorkerRegistrar";

const inter = Inter({ subsets: ["latin"] });

const isDev = process.env.NEXT_PUBLIC_APP_ENV === "dev";
const themeColor = isDev ? "#CA8A04" : "#2563eb";
const titlePrefix = isDev ? "[DEV] " : "";

export const metadata: Metadata = {
  title: `${titlePrefix}ClearBag - 学校配布物AIアシスタント`,
  description: "学校のお便りをAIが自動解析。カレンダー・タスクに一括登録。",
  manifest: "/manifest.webmanifest",
  icons: {
    icon: "/icon.svg",
    apple: "/apple-icon.png",
  },
  appleWebApp: {
    capable: true,
    statusBarStyle: "default",
    title: `${titlePrefix}ClearBag`,
  },
};

export const viewport: Viewport = {
  themeColor: themeColor,
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="ja">
      <body className={`${inter.className} min-h-screen bg-gray-50`}>
        <ServiceWorkerRegistrar />
        {children}
      </body>
    </html>
  );
}
