// app/layout.tsx
import type { Metadata, Viewport } from "next";
import { Outfit, Manrope, Noto_Sans_KR } from "next/font/google";
import MobileBottomNav from "@/components/layout/MobileBottomNav";
import "./globals.css";

// Outfit (제목/로고/영문 강조용)
const outfit = Outfit({
  subsets: ["latin"],
  variable: "--font-outfit",
  display: "swap",
});

// Manrope (본문용 - 영문/숫자 최적화)
const manrope = Manrope({
  subsets: ["latin"],
  variable: "--font-manrope",
  display: "swap",
});

// Noto Sans KR (한글용)
const notoSansKr = Noto_Sans_KR({
  weight: ["400", "500", "700"],
  subsets: ["latin"],
  variable: "--font-noto-sans",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Swell - 패션 코디 추천",
  description: "AI 기반 패션 코디 추천 및 가상 피팅 서비스",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  userScalable: false, // 사용자가 화면 크기를 조절하지 못하도록 설정
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="ko"
      className={`${outfit.variable} ${manrope.variable} ${notoSansKr.variable}`}
    >
      <body className={manrope.className}>
        {children}
        <MobileBottomNav />
      </body>
    </html>
  );
}