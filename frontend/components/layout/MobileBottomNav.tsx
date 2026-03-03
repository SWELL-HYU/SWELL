"use client";

import { useRouter, usePathname } from "next/navigation";
import ClosetIcon from "@/components/common/ClosetIcon";
import HomeIcon from "@/components/common/HomeIcon";
import HeartIcon from "@/components/common/HeartIcon";

export default function MobileBottomNav() {
  const router = useRouter();
  const pathname = usePathname();

  // 하단 네비게이션이 보여질 경로 목록
  const visiblePaths = ["/main", "/closet", "/favorites"];
  const isVisible = pathname && visiblePaths.some((path) => pathname.startsWith(path));

  if (!isVisible) return null;

  const navItems = [
    {
      path: "/closet",
      icon: ClosetIcon,
      onClick: () => router.push("/closet"),
    },
    {
      path: "/main",
      icon: HomeIcon,
      onClick: () => {
        sessionStorage.removeItem("mainPageNavigating");
        router.push("/main");
      },
    },
    {
      path: "/favorites",
      icon: HeartIcon,
      onClick: () => router.push("/favorites"),
    },
  ];

  return (
    <div className="md:hidden fixed bottom-0 left-0 right-0 bg-white border-t border-gray-100 z-[100] pb-[env(safe-area-inset-bottom)] shadow-lg">
      <div className="flex items-center justify-around h-14 px-4">
        {navItems.map((item) => {
          const isActive = pathname === item.path;
          const IconComponent = item.icon;
          return (
            <button
              key={item.path}
              onClick={item.onClick}
              className={`flex items-center justify-center w-12 h-12 rounded-full transition-all cursor-pointer active:scale-90 ${isActive
                ? "bg-[#5697B0]/10 text-[#5697B0]"
                : "text-gray-400 active:bg-gray-100"
                }`}
            >
              <IconComponent
                size={24}
                filled={isActive && item.path === "/favorites"}
                className="transition-transform"
              />
            </button>
          );
        })}
      </div>
    </div>
  );
}
