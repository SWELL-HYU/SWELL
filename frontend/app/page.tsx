"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

export default function Home() {
  const router = useRouter();
  const [fadeOut, setFadeOut] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => {
      setFadeOut(true);
      setTimeout(() => {
        router.push("/start");
      }, 800); // 회전 + 확대 애니메이션 시간
    }, 3000);

    return () => clearTimeout(timer);
  }, [router]);

  return (
    <div
      className="relative min-h-screen flex items-center justify-center bg-cover bg-center bg-no-repeat"
      style={{ backgroundImage: "url('/images/start_bg.png')" }}
    >
      {/* 반투명 오버레이 */}
      <div className="absolute inset-0 bg-white/20"></div>

      {/* 로고 애니메이션 */}
      <div className="relative flex items-center justify-center">
        <img
          src="/videos/swell_spin.gif"
          alt="Swell Logo"
          className={`w-36 h-36 object-contain transition-all duration-[800ms] ${
            fadeOut ? "scale-0 rotate-[0deg] opacity-0" : "scale-100 rotate-0 opacity-100"
          }`}
        />
      </div>
    </div>
  );
}
