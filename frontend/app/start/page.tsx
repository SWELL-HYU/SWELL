"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Image from "next/image";
import { login, signup } from "@/lib/auth";

export default function StartPage() {
  const router = useRouter();

  // Layout State
  const [currentPage, setCurrentPage] = useState(0);

  // View Mode: 'gender' (default) | 'admin'
  const [isAdminMode, setIsAdminMode] = useState(false);

  // Generic Loading/Error
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Admin Auth State
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [name, setName] = useState("");
  const [adminGender, setAdminGender] = useState<"male" | "female" | "">("");

  // 설명서 페이지 내용 (4페이지)
  const guidePages = [
    { title: "Welcome to Swell", desc: "swell에 방문하신 모두를 환영합니다" },
    { title: "스와이프하며 코디 구경", desc: "마음에 드는 코디를 좌우로 넘기며 탐색해보세요!" },
    { title: "Find your Shell", desc: "이 뿐만 아니라, 당신이 고른 상품을 AI를 통해 입어볼 수도 있습니다. 매장에 방문하지 않고서도 말이죠!" },
    { title: "", desc: "swell에 가입하고, 이 놀라운 서비스를 직접 경험해보세요!" },
  ];

  // 1. 일반 사용자: 성별 선택 -> 자동 가입 -> 자동 로그인
  const handleGenderSelect = async (selectedGender: "male" | "female") => {
    if (loading) return;
    setLoading(true);
    setError("");

    try {
      const timestamp = Date.now();
      const randomNumber = Math.floor(Math.random() * 9000) + 1000; // 4자리 랜덤 숫자
      const randomId = Math.random().toString(36).substring(2, 8);

      const genEmail = `user_${timestamp}_${randomId}@swell.temp`;
      const genPassword = `pass_${timestamp}_${randomId}`;
      const genName = `테스트 유저 ${randomNumber}`;

      // 1. 회원가입
      await signup({
        email: genEmail,
        password: genPassword,
        name: genName,
        gender: selectedGender,
      });

      // 2. 로그인
      const response = await login({
        email: genEmail,
        password: genPassword,
      });

      // 3. 이동
      if (response.data.user.hasCompletedOnboarding) {
        router.push("/main");
      } else {
        router.push("/onboarding");
      }
    } catch (err: any) {
      const errorMessage = err.response?.data?.error?.message || "오류가 발생했습니다. 다시 시도해주세요.";
      setError(errorMessage);
      console.error("Auth Error:", err);
      setLoading(false);
    }
  };

  // 2. 관리자/기존 로직: 수동 로그인/가입
  const handleAdminAuth = async () => {
    setError("");
    setLoading(true);

    try {
      if (isLogin) {
        // Login
        const response = await login({ email, password });
        if (response.data.user.hasCompletedOnboarding) {
          router.push("/main");
        } else {
          router.push("/onboarding");
        }
      } else {
        // Signup
        if (!email || !password || !name || !adminGender) {
          throw new Error("모든 항목을 입력해주세요.");
        }
        if (password !== confirmPassword) {
          throw new Error("비밀번호가 일치하지 않습니다.");
        }
        await signup({ email, password, name, gender: adminGender as "male" | "female" });
        alert("회원가입 완료! 로그인해주세요.");
        setIsLogin(true); // 로그인 화면으로 전환
        setLoading(false);
      }
    } catch (err: any) {
      const errorMessage = err.response?.data?.error?.message || err.message || "오류가 발생했습니다.";
      setError(errorMessage);
      setLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      if (isAdminMode) handleAdminAuth();
    }
  };

  return (
    <div
      className="relative min-h-[100dvh] flex items-center justify-center p-4 md:p-8 bg-cover bg-center bg-no-repeat"
      style={{ backgroundImage: "url('/images/start_bg.png')" }}
    >
      {/* 데스크톱 레이아웃 */}
      <div className="hidden md:flex gap-6 max-w-[1200px] mx-auto">

        {/* 왼쪽 영역: 인증 카드 */}
        <div className="flex flex-col gap-6 w-[500px] h-[660px]">

          {/* 메인 카드 (Glassmorphism) */}
          <div
            className={`flex-1 rounded-[10px] p-8 flex flex-col backdrop-blur-xl shadow-2xl border border-white/40 justify-center transition-all duration-500 relative overflow-hidden`}
            style={{ backgroundColor: "rgba(235, 235, 230, 0.6)" }}
          >
            {/* 상단 헤더 영역 - Admin Mode일 때는 공간 확보를 위해 타이틀 축소/숨김 */}
            <div className={`text-center relative z-10 ${isAdminMode ? 'mb-2' : 'mb-8'}`}>
              {!isAdminMode && (
                <h1 className="text-[40px] leading-[48px] text-gray-900 font-outfit mb-3">
                  Swell
                </h1>
              )}
              <p className={`text-gray-600 font-manrope ${isAdminMode ? 'text-[20px] font-bold text-gray-800' : 'text-[16px]'}`}>
                {isAdminMode
                  ? (isLogin ? "Admin Login" : "Create Admin Account")
                  : "성별을 선택하고 시작하세요"}
              </p>
            </div>

            {/* Error Message */}
            {error && (
              <p className="text-red-500 text-sm text-center mb-4 px-4 bg-red-50/50 py-2 rounded-lg relative z-10">
                {error}
              </p>
            )}

            {/* Content Switcher */}
            <div className="relative z-10 w-full px-8">
              {!isAdminMode ? (
                // === 일반 사용자 모드 (성별 선택) ===
                <div className="flex flex-col gap-4">
                  <button
                    onClick={() => handleGenderSelect("female")}
                    disabled={loading}
                    className="group relative w-full h-[80px] bg-white/60 hover:bg-white/80 rounded-2xl border border-white/40 transition-all shadow-sm hover:shadow-md flex items-center justify-between px-8"
                  >
                    <span className="text-[20px] font-medium text-gray-800 font-manrope">여성</span>
                    <div className="w-8 h-8 rounded-full border border-gray-400 flex items-center justify-center group-hover:border-black transition-colors">
                      <div className="w-5 h-5 bg-black rounded-full opacity-0 group-hover:opacity-100 transition-opacity" />
                    </div>
                  </button>

                  <button
                    onClick={() => handleGenderSelect("male")}
                    disabled={loading}
                    className="group relative w-full h-[80px] bg-white/60 hover:bg-white/80 rounded-2xl border border-white/40 transition-all shadow-sm hover:shadow-md flex items-center justify-between px-8"
                  >
                    <span className="text-[20px] font-medium text-gray-800 font-manrope">남성</span>
                    <div className="w-8 h-8 rounded-full border border-gray-400 flex items-center justify-center group-hover:border-black transition-colors">
                      <div className="w-5 h-5 bg-black rounded-full opacity-0 group-hover:opacity-100 transition-opacity" />
                    </div>
                  </button>

                  {/* Admin Toggle Link (Centered) */}
                  <button
                    onClick={() => {
                      setIsAdminMode(true);
                      setError("");
                    }}
                    className="mt-6 text-sm text-gray-400 hover:text-gray-800 transition-colors font-medium border-b border-transparent hover:border-gray-800 self-center w-fit mx-auto"
                  >
                    Admin Access
                  </button>
                </div>
              ) : (
                // === 관리자 모드 (이메일 로그인/가입) ===
                <div className="animate-fadeIn flex flex-col h-full">
                  {/* Login / Signup Toggle Tabs */}
                  <div className="flex bg-gray-100/50 p-1 rounded-xl mb-4 border border-white/20">
                    <button
                      onClick={() => { setIsLogin(true); setError(""); }}
                      className={`flex-1 py-2 text-sm font-semibold rounded-lg transition-all duration-300 ${isLogin ? 'bg-white shadow-[0_2px_8px_rgba(0,0,0,0.08)] text-gray-900' : 'text-gray-500 hover:text-gray-700'}`}
                    >
                      Login
                    </button>
                    <button
                      onClick={() => { setIsLogin(false); setError(""); }}
                      className={`flex-1 py-2 text-sm font-semibold rounded-lg transition-all duration-300 ${!isLogin ? 'bg-white shadow-[0_2px_8px_rgba(0,0,0,0.08)] text-gray-900' : 'text-gray-500 hover:text-gray-700'}`}
                    >
                      Sign Up
                    </button>
                  </div>

                  <div className="space-y-2">
                    <input
                      type="email"
                      placeholder="Email Address"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      onKeyPress={handleKeyPress}
                      className="w-full h-[46px] px-4 bg-white/70 border border-white/40 rounded-xl outline-none text-gray-800 placeholder:text-gray-400 focus:bg-white focus:border-gray-300 transition-all font-manrope text-[14px]"
                    />
                    <input
                      type="password"
                      placeholder="Password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      onKeyPress={handleKeyPress}
                      className="w-full h-[46px] px-4 bg-white/70 border border-white/40 rounded-xl outline-none text-gray-800 placeholder:text-gray-400 focus:bg-white focus:border-gray-300 transition-all font-manrope text-[14px]"
                    />

                    {!isLogin && (
                      <div className="space-y-2 animate-fadeIn">
                        <input
                          type="password"
                          placeholder="Confirm Password"
                          value={confirmPassword}
                          onChange={(e) => setConfirmPassword(e.target.value)}
                          onKeyPress={handleKeyPress}
                          className="w-full h-[46px] px-4 bg-white/70 border border-white/40 rounded-xl outline-none text-gray-800 placeholder:text-gray-400 focus:bg-white focus:border-gray-300 transition-all font-manrope text-[14px]"
                        />
                        <input
                          type="text"
                          placeholder="Display Name"
                          value={name}
                          onChange={(e) => setName(e.target.value)}
                          onKeyPress={handleKeyPress}
                          className="w-full h-[46px] px-4 bg-white/70 border border-white/40 rounded-xl outline-none text-gray-800 placeholder:text-gray-400 focus:bg-white focus:border-gray-300 transition-all font-manrope text-[14px]"
                        />

                        {/* Improved Gender Selection */}
                        <div className="flex gap-3 pt-1">
                          <button
                            onClick={() => setAdminGender('male')}
                            className={`flex-1 h-[44px] rounded-xl border flex items-center justify-center gap-2 transition-all ${adminGender === 'male' ? 'bg-gray-900 text-white border-gray-900 shadow-md' : 'bg-white/50 border-white/40 text-gray-600 hover:bg-white/80'}`}
                          >
                            <span className="text-sm font-medium">Male</span>
                          </button>
                          <button
                            onClick={() => setAdminGender('female')}
                            className={`flex-1 h-[44px] rounded-xl border flex items-center justify-center gap-2 transition-all ${adminGender === 'female' ? 'bg-gray-900 text-white border-gray-900 shadow-md' : 'bg-white/50 border-white/40 text-gray-600 hover:bg-white/80'}`}
                          >
                            <span className="text-sm font-medium">Female</span>
                          </button>
                        </div>
                      </div>
                    )}
                  </div>

                  <button
                    onClick={handleAdminAuth}
                    disabled={loading}
                    className="w-full h-[50px] bg-gray-900 text-white rounded-xl flex items-center justify-center hover:bg-black hover:shadow-lg disabled:opacity-70 disabled:hover:shadow-none transition-all mt-4 font-bold text-[15px] tracking-wide"
                  >
                    {loading ? <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" /> : (isLogin ? "Sign In" : "Create Account")}
                  </button>

                  <button
                    onClick={() => {
                      setIsAdminMode(false);
                      setError("");
                    }}
                    className="mt-3 text-xs text-gray-400 hover:text-gray-800 transition-colors font-medium border-b border-transparent hover:border-gray-800 self-center w-fit"
                  >
                    Back to Selection
                  </button>
                </div>
              )}
            </div>

            {/* Loading Overlay */}
            {loading && !isAdminMode && (
              <div className="absolute inset-0 bg-white/50 backdrop-blur-sm rounded-[10px] flex flex-col items-center justify-center z-30">
                <div className="w-10 h-10 border-4 border-black border-t-transparent rounded-full animate-spin mb-4" />
                <p className="text-gray-800 font-medium animate-pulse">Creating your account...</p>
              </div>
            )}
          </div>

          {/* 프로모 카드 - 유지 */}
          {/* 프로모 카드 */}
          <div
            className={`rounded-[10px] flex flex-col backdrop-blur-2xl shadow-2xl border border-white/10 relative overflow-hidden transition-all duration-500 ${isAdminMode && !isLogin ? "min-h-[60px] p-4 justify-center" : "min-h-[200px] p-6"
              }`}
            style={{ backgroundColor: "rgba(20, 24, 28, 0.9)" }}
          >
            {isAdminMode && !isLogin ? (
              <div className="flex justify-between items-center relative z-10">
                <span className="text-white/90 font-outfit text-lg font-bold">Swell Archive</span>
                <div className="w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse" />
              </div>
            ) : (
              <>
                <div className="flex justify-between items-start mb-2 relative z-10">
                  <span className="text-white/60 font-outfit text-sm">New In</span>
                  <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                </div>
                <h3 className="text-white font-outfit text-2xl font-bold mb-1 relative z-10">
                  Swell<br />Archive
                </h3>
                <p className="text-white/40 text-xs font-manrope mt-auto relative z-10">
                  Discover the latest collection &rarr;
                </p>
              </>
            )}
          </div>
        </div>

        {/* 오른쪽 - 설명서 카드 (변경 없음) */}
        <div className="w-[500px] h-[660px]">
          <div
            className="rounded-[10px] h-full p-10 flex flex-col backdrop-blur-3xl shadow-2xl border border-white/50 justify-between"
            style={{ backgroundColor: "rgba(253, 249, 247, 0.9)" }}
          >
            {/* Background Decor */}
            <div className="absolute top-0 right-0 p-4 overflow-hidden pointer-events-none select-none">
              <span className="text-[180px] leading-none font-bold font-outfit text-black/[0.03] tracking-tighter -mr-10 -mt-10 block">
                0{currentPage + 1}
              </span>
            </div>
            {/* Soft Gradient Blob */}
            <div className={`absolute top-1/3 left-1/2 -translate-x-1/2 w-64 h-64 rounded-full bg-gradient-to-tr from-orange-100/60 to-rose-100/40 blur-3xl pointer-events-none transition-all duration-700 ${currentPage % 2 === 0 ? 'scale-100 opacity-70' : 'scale-110 opacity-50'}`} />

            {/* 상단 페이지 표시 */}
            <div className="flex justify-between items-start relative z-10">
              <div className="h-1 w-10 bg-black rounded-full" />
            </div>

            {/* 메인 컨텐츠 영역 */}
            <div className="flex-1 flex flex-col justify-center relative z-10 pl-4">
              {currentPage === 0 && (
                <div className="flex flex-col animate-fadeIn">
                  <h2 className="text-[56px] leading-[1.1] font-bold text-gray-900 font-outfit mb-6 tracking-tight">
                    Welcome<br />
                    <span className="text-gray-400">to Swell.</span>
                  </h2>
                  <p className="text-[16px] text-gray-600 font-manrope leading-relaxed max-w-[280px] mb-10 pl-1 border-l-2 border-gray-200">
                    당신의 취향을 발견하세요<br />
                    Start your fashion journey.
                  </p>
                  <div className="w-[200px] h-[200px] relative drop-shadow-2xl self-center mt-8 hover:scale-110 transition-transform duration-500">
                    <Image
                      src="/images/swell_wo_bg.png"
                      alt="Swell Logo"
                      fill
                      className="object-contain"
                    />
                  </div>
                </div>
              )}

              {currentPage === 1 && (
                <div className="flex flex-col animate-fadeIn w-full relative">
                  <div className="absolute -right-4 top-0 w-32 h-32 bg-gray-100 rounded-full -z-10" />
                  <h2 className="text-[42px] font-bold text-gray-900 font-outfit mb-2">
                    Swipe<br />
                    <span className="font-light italic">& Like</span>
                  </h2>
                  <div className="flex gap-4 mb-4 mt-8">
                    <div className="w-16 h-16 bg-white rounded-2xl flex items-center justify-center shadow-lg transform -rotate-3 hover:rotate-0 transition-transform">
                      <Image src="/images/finger.png" alt="Swipe" width={32} height={32} className="object-contain" />
                    </div>
                    <div className="w-16 h-16 bg-black text-white rounded-2xl flex items-center justify-center shadow-lg transform translate-y-4 hover:translate-y-2 transition-transform">
                      <Image src="/images/heart.png" alt="Like" width={32} height={32} className="object-contain invert brightness-0" />
                    </div>
                  </div>
                  <p className="text-[15px] text-gray-600 font-manrope leading-relaxed max-w-[260px] mt-8">
                    스왑으로 코디를 구경하며,<br />
                    마음에 드는 코디를 저장하세요!
                  </p>
                </div>
              )}

              {currentPage === 2 && (
                <div className="flex flex-col animate-fadeIn">
                  <h2 className="text-[42px] font-bold text-gray-900 font-outfit mb-4 text-right pr-4">
                    Virtual<br />Fitting
                  </h2>
                  <div className="relative w-full h-[220px] mb-6">
                    <div className="absolute right-10 top-10 w-40 h-40 border-2 border-gray-200 rounded-full" />
                    <div className="absolute left-4 top-0 w-[240px] h-[200px] drop-shadow-2xl transform hover:scale-105 transition-transform duration-500">
                      <Image
                        src="/images/mirror.png"
                        alt="Virtual Fitting"
                        fill
                        className="object-contain"
                      />
                    </div>
                  </div>
                  <p className="text-[15px] text-gray-600 font-manrope leading-relaxed text-right pr-4">
                    swell의 가상 피팅 AI로<br />
                    매장 방문 없이도 옷을 입어보세요!
                  </p>
                </div>
              )}

              {currentPage === 3 && (
                <div className="flex flex-col animate-fadeIn pl-2">
                  <div className="w-12 h-12 bg-black rounded-full flex items-center justify-center mb-6 shadow-xl">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                      <path d="M5 12L10 17L19 8" stroke="white" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                  </div>
                  <h2 className="text-[48px] font-bold text-gray-900 font-outfit mb-4 leading-tight">
                    Ready<br />to Start?
                  </h2>
                </div>
              )}
            </div>

            {/* 하단 네비게이션 */}
            <div className="flex items-center justify-between pt-6 border-t border-gray-200/30 relative z-10">
              <div className="flex gap-4">
                {guidePages.map((_, i) => (
                  <button
                    key={i}
                    onClick={() => setCurrentPage(i)}
                    className={`transition-all duration-300 ${i === currentPage ? "w-8 h-1.5 bg-black rounded-full" : "w-1.5 h-1.5 bg-gray-300 rounded-full hover:bg-gray-400"
                      }`}
                  />
                ))}
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => setCurrentPage(Math.max(0, currentPage - 1))}
                  disabled={currentPage === 0}
                  className="w-10 h-10 rounded-full flex items-center justify-center border border-gray-200 hover:bg-black hover:text-white hover:border-black disabled:opacity-0 transition-all text-gray-600"
                >
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M15 18L9 12L15 6" />
                  </svg>
                </button>
                <button
                  onClick={() => setCurrentPage(Math.min(guidePages.length - 1, currentPage + 1))}
                  disabled={currentPage === guidePages.length - 1}
                  className="w-10 h-10 rounded-full flex items-center justify-center border border-gray-200 hover:bg-black hover:text-white hover:border-black disabled:opacity-0 transition-all text-gray-600"
                >
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M9 18L15 12L9 6" />
                  </svg>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* 모바일 레이아웃 */}
      <div className="md:hidden absolute inset-0 flex flex-col justify-center px-6 pb-[calc(6rem+env(safe-area-inset-bottom))]">
        <div className="w-full max-w-[300px] mx-auto animate-fadeIn">
          {/* 헤더 */}
          <div className="flex justify-between items-center mb-8">
            <h1 className="text-[28px] font-bold text-gray-900 font-outfit tracking-tight drop-shadow-md">
              Swell
            </h1>
            <p className="text-gray-600 text-sm">
              {isAdminMode
                ? (isLogin ? "Admin Login" : "Admin Sign Up")
                : "성별을 선택하고 시작하세요"}
            </p>
          </div>

          {error && (
            <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-2 mb-4">
              <p className="text-red-700 text-[11px] font-medium text-center">{error}</p>
            </div>
          )}

          {!isAdminMode ? (
            <div className="space-y-3">
              <button
                onClick={() => handleGenderSelect("female")}
                disabled={loading}
                className="w-full h-[60px] bg-white rounded-xl border border-gray-200 flex items-center justify-between px-6 hover:border-black transition-all active:scale-[0.98]"
              >
                <span className="font-medium text-gray-900">여성</span>
                <div className="w-4 h-4 rounded-full border border-gray-300" />
              </button>

              <button
                onClick={() => handleGenderSelect("male")}
                disabled={loading}
                className="w-full h-[60px] bg-white rounded-xl border border-gray-200 flex items-center justify-between px-6 hover:border-black transition-all active:scale-[0.98]"
              >
                <span className="font-medium text-gray-900">남성</span>
                <div className="w-4 h-4 rounded-full border border-gray-300" />
              </button>
            </div>
          ) : (
            <div className="space-y-3">
              {/* Mobile Admin Tabs */}
              <div className="flex bg-white/40 p-1 rounded-xl mb-3">
                <button
                  onClick={() => { setIsLogin(true); setError(""); }}
                  className={`flex-1 py-1.5 text-xs font-medium rounded-lg transition-all ${isLogin ? 'bg-white shadow-sm text-black' : 'text-gray-500'}`}
                >
                  Login
                </button>
                <button
                  onClick={() => { setIsLogin(false); setError(""); }}
                  className={`flex-1 py-1.5 text-xs font-medium rounded-lg transition-all ${!isLogin ? 'bg-white shadow-sm text-black' : 'text-gray-500'}`}
                >
                  Sign Up
                </button>
              </div>

              <input
                type="email"
                placeholder="Email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full h-[44px] px-4 bg-white/70 border border-white/40 rounded-xl outline-none text-[13px] font-medium placeholder:text-gray-500/80"
              />
              <input
                type="password"
                placeholder="Password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full h-[44px] px-4 bg-white/70 border border-white/40 rounded-xl outline-none text-[13px] font-medium placeholder:text-gray-500/80"
              />

              {!isLogin && (
                <>
                  <input
                    type="password"
                    placeholder="Confirm PW"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    className="w-full h-[44px] px-4 bg-white/70 border border-white/40 rounded-xl outline-none text-[13px] font-medium placeholder:text-gray-500/80"
                  />
                  <input
                    type="text"
                    placeholder="Name"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    className="w-full h-[44px] px-4 bg-white/70 border border-white/40 rounded-xl outline-none text-[13px] font-medium placeholder:text-gray-500/80"
                  />
                  <div className="flex gap-4 justify-center py-1">
                    <label className="text-xs flex gap-1 items-center"><input type="radio" checked={adminGender === 'male'} onChange={() => setAdminGender('male')} /> Male</label>
                    <label className="text-xs flex gap-1 items-center"><input type="radio" checked={adminGender === 'female'} onChange={() => setAdminGender('female')} /> Female</label>
                  </div>
                </>
              )}

              <button
                onClick={handleAdminAuth}
                disabled={loading}
                className="w-full h-[50px] bg-black text-white rounded-xl flex items-center justify-center hover:bg-gray-900 disabled:opacity-50 transition-all shadow-lg text-[14px] font-bold mt-4"
              >
                {loading ? <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" /> : (isLogin ? "Login" : "Sign Up")}
              </button>

              <button
                onClick={() => {
                  setIsAdminMode(false);
                  setError("");
                }}
                className="mt-4 text-xs font-medium text-gray-400 hover:text-black transition-colors border-b border-transparent hover:border-black mx-auto block"
              >
                Back to Selection
              </button>
            </div>
          )}

          {loading && !isAdminMode && (
            <div className="mt-6 flex justify-center">
              <div className="w-6 h-6 border-2 border-black border-t-transparent rounded-full animate-spin" />
            </div>
          )}

          {!isAdminMode && (
            <div className="flex justify-center mt-6">
              <button
                onClick={() => {
                  setIsAdminMode(true);
                  setError("");
                }}
                className="text-[11px] uppercase font-bold text-gray-400 hover:text-black tracking-widest px-2"
              >
                For Admin
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}