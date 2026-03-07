"use client";

import { usePathname } from "next/navigation";
import { useEffect } from "react";
import { sendPageView } from "@/lib/analytics";

export function PageViewTracker() {
  const pathname = usePathname();

  useEffect(() => {
    sendPageView(pathname);
  }, [pathname]);

  return null;
}
