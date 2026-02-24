"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";

export function NavBar() {
  const { signOut } = useAuth();
  const pathname = usePathname();

  const links = [
    { href: "/dashboard", label: "ホーム" },
    { href: "/calendar", label: "カレンダー" },
    { href: "/tasks", label: "タスク" },
    { href: "/profiles", label: "プロフィール" },
    { href: "/settings", label: "設定" },
  ];

  return (
    <nav className="bg-white border-b border-gray-200">
      <div className="max-w-2xl mx-auto px-4 flex items-center justify-between h-14">
        <Link href="/dashboard" className="text-blue-600 font-bold text-lg">
          ClearBag
        </Link>

        <div className="flex items-center gap-4">
          {links.map(({ href, label }) => (
            <Link
              key={href}
              href={href}
              className={`text-sm ${
                pathname === href
                  ? "text-blue-600 font-semibold"
                  : "text-gray-500 hover:text-gray-800"
              }`}
            >
              {label}
            </Link>
          ))}

          <button
            onClick={signOut}
            className="text-sm text-gray-400 hover:text-gray-600"
          >
            サインアウト
          </button>
        </div>
      </div>
    </nav>
  );
}
