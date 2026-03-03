import type { MetadataRoute } from "next";

export const dynamic = "force-static";

export default function manifest(): MetadataRoute.Manifest {
  const isDev = process.env.NEXT_PUBLIC_APP_ENV === "dev";
  const themeColor = isDev ? "#CA8A04" : "#2563EB";
  const namePrefix = isDev ? "[DEV] " : "";
  const appId = isDev ? "/?app=clearbag-dev" : "/?app=clearbag-prod";

  return {
    id: appId,
    name: `${namePrefix}ClearBag - 学校配布物AIアシスタント`,
    short_name: `${namePrefix}ClearBag`,
    description: "学校のお便りをAIが自動解析。カレンダー・タスクに一括登録。",
    start_url: "/dashboard",
    display: "standalone",
    background_color: "#f9fafb",
    theme_color: themeColor,
    orientation: "portrait",
    icons: [
      {
        src: "/icon-192.png",
        sizes: "192x192",
        type: "image/png",
        purpose: "any",
      },
      {
        src: "/icon-192.png",
        sizes: "192x192",
        type: "image/png",
        purpose: "maskable",
      },
      {
        src: "/icon-512.png",
        sizes: "512x512",
        type: "image/png",
        purpose: "any",
      },
      {
        src: "/icon-512.png",
        sizes: "512x512",
        type: "image/png",
        purpose: "maskable",
      },
    ],
    share_target: {
      action: "/share-target/",
      method: "POST",
      enctype: "multipart/form-data",
      params: {
        files: [
          {
            name: "file",
            accept: [
              "application/pdf",
              "image/jpeg",
              "image/png",
              "image/webp",
              "image/heic",
              "image/*",
              ".pdf",
              ".jpg",
              ".jpeg",
              ".png",
              ".webp",
              ".heic",
            ],
          },
        ],
      },
    },
  };
}
