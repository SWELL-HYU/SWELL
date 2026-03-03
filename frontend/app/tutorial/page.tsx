"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Image from "next/image";
import { motion, AnimatePresence } from "framer-motion";
import {
    Heart,
    Shirt,
    ShoppingBag,
    ChevronUp,
    Pointer,
    Hand,
    MoveHorizontal,
    MoveVertical,
    X,
    Check,
    ArrowUp
} from "lucide-react";

export default function TutorialPage() {
    const router = useRouter();
    const [step, setStep] = useState(0);
    const [isDesktop, setIsDesktop] = useState(false);
    const [mounted, setMounted] = useState(false);

    useEffect(() => {
        setMounted(true);
        const checkDesktop = () => setIsDesktop(window.innerWidth >= 768);
        checkDesktop();
        window.addEventListener('resize', checkDesktop);
        return () => window.removeEventListener('resize', checkDesktop);
    }, []);

    // 모바일용 단계
    const mobileSteps = [
        // Step 1: 좌우 스와이프 (탐색)
        {
            id: "swipe",
            render: () => (
                <div className="relative w-full h-full flex flex-col items-center justify-center pointer-events-none">
                    {/* 가이드 애니메이션 */}
                    <div className="relative w-64 h-64 mb-8 flex items-center justify-center">
                        <motion.div
                            className="absolute z-10"
                            animate={{ x: [-50, 50, -50] }}
                            transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
                        >
                            <img src="/images/finger.png" alt="Hand" className="w-16 h-16 object-contain drop-shadow-xl" />
                        </motion.div>

                        {/* 스와이프 궤적 표시 */}
                        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-40 h-16 flex items-center justify-between opacity-50">
                            <div className="w-2 h-2 bg-white rounded-full ml-2" />
                            <div className="flex-1 h-0.5 bg-white mx-2" />
                            <div className="w-2 h-2 bg-white rounded-full mr-2" />
                        </div>
                    </div>

                    <div className="text-center px-8 z-20">
                        <h2 className="text-2xl font-bold text-white mb-4 drop-shadow-lg">
                            좌우로 스와이프
                        </h2>
                        <p className="text-white/90 text-lg font-medium drop-shadow-md leading-relaxed">
                            스와이프하여 더 많은<br />코디를 확인하세요!
                        </p>
                    </div>
                </div>
            )
        },
        // Step 2: 좋아요 (더블탭/클릭)
        {
            id: "like",
            render: () => (
                <div className="relative w-full h-full flex flex-col items-center justify-center pointer-events-none">
                    {/* 하이라이트 원: 우측 상단 (배경 이미지의 하트 위치 보정) */}
                    <div className="absolute top-[7.5%] right-[6.5%] w-14 h-14 rounded-full border-4 border-white shadow-[0_0_15px_rgba(255,255,255,0.8)] animate-pulse z-10" />

                    {/* 중앙 가이드 */}
                    <div
                        className="relative mb-12 flex flex-col items-center"
                        style={{ transform: "translate(5px, 0px)" }} // 위치 미세 조정을 위한 값 (x, y)
                    >
                        <motion.div
                            initial={{ scale: 1 }}
                            animate={{ scale: [1, 0.8, 1, 0.8, 1] }}
                            transition={{ duration: 1.5, repeat: Infinity, repeatDelay: 1 }}
                            className="relative z-0"
                        >
                            <img src="/images/heart.png" alt="Heart" className="w-32 h-32 object-contain drop-shadow-2xl" />
                        </motion.div>
                        <motion.div
                            className="absolute bottom-[-10px] right-[-10px] z-10"
                            animate={{ rotate: [-10, 0, -10], scale: [1, 0.9, 1], x: [0, -5, 0], y: [0, -5, 0] }}
                            transition={{ duration: 1, repeat: Infinity }}
                        >
                            <img src="/images/finger.png" alt="Hand" className="w-16 h-16 object-contain drop-shadow-xl" />
                        </motion.div>
                    </div>

                    <div className="text-center px-8 z-20 mt-12">
                        <h2 className="text-2xl font-bold text-white mb-3 drop-shadow-lg">
                            좋아요 & 저장
                        </h2>
                        <p className="text-white/90 text-lg font-medium drop-shadow-md leading-relaxed">
                            더블클릭하거나<br />
                            우측 상단을 누르면 좋아요!
                        </p>
                        <p className="text-white/70 text-sm mt-2">
                            마음에 드는 코디를 저장해두세요.
                        </p>
                    </div>
                </div>
            )
        },
        // Step 3: 상세 보기 (위로 스와이프)
        {
            id: "detail",
            render: () => (
                <div className="relative w-full h-full flex flex-col items-center justify-end pb-32 pointer-events-none">
                    {/* 가이드 애니메이션 */}
                    <div className="relative w-full flex justify-center mb-8 h-40">
                        <motion.div
                            className="flex flex-col items-center absolute bottom-0"
                            animate={{ y: [0, -100, 0], opacity: [0, 1, 0] }}
                            transition={{ duration: 2, repeat: Infinity, ease: "easeOut" }}
                        >
                            <img src="/images/finger.png" alt="Hand" className="w-16 h-16 object-contain drop-shadow-xl" />
                        </motion.div>

                        {/* 화살표 표시 */}
                        <div className="absolute bottom-20 flex flex-col items-center opacity-50">
                            <ChevronUp className="w-8 h-8 text-white animate-bounce" />
                            <ChevronUp className="w-8 h-8 text-white -mt-4 animate-bounce delay-75" />
                        </div>
                    </div>

                    <div className="text-center px-8 z-20">
                        <h2 className="text-2xl font-bold text-white mb-3 drop-shadow-lg">
                            상세 아이템 보기
                        </h2>
                        <p className="text-white/90 text-lg font-medium drop-shadow-md leading-relaxed">
                            아래에서 위로 슬라이드하여<br />
                            상세 아이템을 확인하세요!
                        </p>
                    </div>
                </div>
            )
        },
        // Step 4: 메인 기능 (상단 바)
        {
            id: "features",
            render: () => (
                <div className="relative w-full h-full pointer-events-none">
                    {/* 가상 피팅 (왼쪽 탭) */}
                    <div className="absolute top-[5%] left-[25%] -translate-x-1/2 flex flex-col items-center gap-4">
                        <motion.div
                            className="absolute top-12"
                            animate={{ y: [0, -8, 0] }}
                            transition={{ duration: 1.5, repeat: Infinity }}
                        >
                            <ArrowUp className="w-10 h-10 text-white drop-shadow-[0_0_10px_rgba(255,255,255,0.6)]" strokeWidth={3} />
                        </motion.div>

                        {/* 툴팁 */}
                        <motion.div
                            initial={{ opacity: 0, scale: 0.9 }}
                            animate={{ opacity: 1, scale: 1 }}
                            transition={{ delay: 0.3 }}
                            className="absolute top-24 bg-white text-gray-800 p-3 rounded-xl shadow-xl w-48 text-xs font-bold text-center"
                        >
                            <p className="mb-1 text-[#5697B0]">가상 피팅</p>
                            여기서 AI와 함께<br />가상 피팅을 경험해보세요!✨
                        </motion.div>
                    </div>

                    {/* 아이템 목록 (오른쪽 탭) */}
                    <div className="absolute top-[5%] left-[75%] -translate-x-1/2 flex flex-col items-center gap-4">
                        <motion.div
                            className="absolute top-12"
                            animate={{ y: [0, -8, 0] }}
                            transition={{ duration: 1.5, repeat: Infinity }}
                        >
                            <ArrowUp className="w-10 h-10 text-white drop-shadow-[0_0_10px_rgba(255,255,255,0.6)]" strokeWidth={3} />
                        </motion.div>

                        {/* 툴팁 */}
                        <motion.div
                            initial={{ opacity: 0, scale: 0.9 }}
                            animate={{ opacity: 1, scale: 1 }}
                            transition={{ delay: 0.5 }}
                            className="absolute top-24 bg-white text-gray-800 p-3 rounded-xl shadow-xl w-48 text-xs font-bold text-center"
                        >
                            <p className="mb-1 text-[#5697B0]">아이템 목록</p>
                            내가 저장한 아이템을<br />한눈에 확인하세요!❤️
                        </motion.div>
                    </div>
                </div>
            )
        },
        // Step 5: 피팅 가이드
        {
            id: "fitting",
            render: () => (
                <div className="relative w-full h-full flex items-center justify-center p-6 pointer-events-none">
                    <div className="bg-white rounded-3xl p-6 shadow-2xl w-full max-w-sm">
                        <div className="text-center mb-6">
                            <h2 className="text-xl font-bold text-gray-900">가상피팅 시작하기</h2>
                        </div>

                        <div className="flex justify-center gap-4 mb-6">
                            {/* 좋은 예 */}
                            <div className="flex flex-col items-center gap-2">
                                <div className="w-24 h-32 bg-gray-100 rounded-lg flex items-center justify-center overflow-hidden border-2 border-green-500 relative">
                                    <div className="w-8 h-8 rounded-full bg-gray-300 absolute top-4" />
                                    <div className="w-12 h-20 bg-gray-400 rounded-t-lg absolute bottom-0" />
                                    <div className="absolute bottom-2 right-2 bg-green-500 text-white rounded-full p-0.5">
                                        <Check size={12} strokeWidth={4} />
                                    </div>
                                </div>
                                <span className="text-xs text-green-600 font-bold">Good</span>
                            </div>

                            {/* 나쁜 예 */}
                            <div className="flex flex-col items-center gap-2">
                                <div className="w-24 h-32 bg-gray-100 rounded-lg flex items-center justify-center overflow-hidden border-2 border-red-500 relative">
                                    <div className="w-16 h-24 bg-gray-400 rounded-t-lg absolute -bottom-4" />
                                    <div className="absolute bottom-2 right-2 bg-red-500 text-white rounded-full p-0.5">
                                        <X size={12} strokeWidth={4} />
                                    </div>
                                </div>
                                <span className="text-xs text-red-500 font-bold">Bad</span>
                            </div>
                        </div>

                        <div className="text-center">
                            <p className="text-gray-700 text-sm font-medium mb-1">
                                정확한 피팅을 위해 <span className="font-bold text-[#5697B0]">전신 사진</span>을 올려주세요.
                            </p>
                            <p className="text-gray-500 text-xs">
                                머리부터 발끝까지 잘 나와야 합니다.
                            </p>
                        </div>
                    </div>
                </div>
            )
        }
    ];

    // 데스크톱용 단계
    const desktopSteps = [
        // Step 1: 화살표 이동 (탐색)
        {
            id: "navigate",
            render: () => (
                <div className="relative w-full h-full flex flex-col items-center justify-center pointer-events-none">
                    {/* 화살표 가이드 */}
                    <div className="absolute top-1/2 left-10 -translate-y-1/2 flex items-center gap-4">
                        <motion.div
                            className="w-16 h-16 rounded-full border-4 border-white flex items-center justify-center"
                            animate={{ x: [-10, 0, -10] }}
                            transition={{ duration: 1.5, repeat: Infinity }}
                        >
                            <div className="text-white text-3xl font-bold">←</div>
                        </motion.div>
                        <div className="text-white font-bold text-shadow">Prev</div>
                    </div>

                    <div className="absolute top-1/2 right-10 -translate-y-1/2 flex items-center gap-4">
                        <div className="text-white font-bold text-shadow">Next</div>
                        <motion.div
                            className="w-16 h-16 rounded-full border-4 border-white flex items-center justify-center"
                            animate={{ x: [10, 0, 10] }}
                            transition={{ duration: 1.5, repeat: Infinity }}
                        >
                            <div className="text-white text-3xl font-bold">→</div>
                        </motion.div>
                    </div>

                    <div className="text-center px-8 z-20">
                        <h2 className="text-3xl font-bold text-white mb-4 drop-shadow-lg">
                            코디 탐색하기
                        </h2>
                        <p className="text-white/90 text-xl font-medium drop-shadow-md leading-relaxed">
                            화살표를 클릭하여<br />다양한 코디를 만나보세요!
                        </p>
                    </div>
                </div>
            )
        },
        // Step 2: 좋아요 (클릭)
        {
            id: "like",
            render: () => (
                <div className="relative w-full h-full flex flex-col items-center justify-center pointer-events-none">
                    {/* 하이라이트 원: 우측 상단 */}
                    <div className="absolute top-[16%] right-[32%] xl:right-[35%] w-14 h-14 rounded-full border-4 border-white shadow-[0_0_15px_rgba(255,255,255,0.8)] animate-pulse z-10" />

                    <div className="relative mb-8 flex flex-col items-center">
                        <motion.div
                            initial={{ scale: 1 }}
                            animate={{ scale: [1, 1.1, 1] }}
                            transition={{ duration: 1, repeat: Infinity }}
                        >
                            <img src="/images/heart.png" alt="Heart" className="w-32 h-32 object-contain drop-shadow-2xl" />
                        </motion.div>
                        <div className="absolute bottom-[-20px] right-[-20px]">
                            <Pointer className="w-16 h-16 text-white drop-shadow-xl fill-white/20" />
                        </div>
                    </div>

                    <div className="text-center px-8 z-20 mt-8">
                        <h2 className="text-3xl font-bold text-white mb-3 drop-shadow-lg">
                            좋아요 & 저장
                        </h2>
                        <p className="text-white/90 text-xl font-medium drop-shadow-md leading-relaxed">
                            더블 클릭하거나<br />하트 버튼을 눌러보세요!
                        </p>
                    </div>
                </div>
            )
        },
        // Step 3: 상세 보기 (우측 패널)
        {
            id: "features",
            render: () => (
                <div className="relative w-full h-full pointer-events-none">
                    {/* 우측 패널 하이라이트 */}
                    <div className="absolute top-20 right-10 w-[400px] h-[600px] border-4 border-[#5697B0] border-dashed rounded-xl bg-[#5697B0]/10 backdrop-blur-sm z-10 flex items-center justify-center">
                        <p className="text-white font-bold text-xl drop-shadow-md">Item List Area</p>
                    </div>

                    <div className="absolute top-1/2 left-32 -translate-y-1/2 text-left z-20">
                        <h2 className="text-3xl font-bold text-white mb-4 drop-shadow-lg">
                            상세 아이템 확인
                        </h2>
                        <p className="text-white/90 text-xl font-medium drop-shadow-md leading-relaxed">
                            우측 패널에서<br />코디에 사용된 아이템을<br />바로 확인할 수 있어요.
                        </p>
                    </div>
                </div>
            )
        },
        // Step 4: 옷장 가기 (플로팅 버튼)
        {
            id: "closet",
            render: () => (
                <div className="relative w-full h-full pointer-events-none">
                    {/* 플로팅 버튼 하이라이트 */}
                    <div className="absolute bottom-10 right-12 w-20 h-20 rounded-full border-4 border-[#5697B0] shadow-[0_0_20px_rgba(86,151,176,0.6)] animate-pulse z-10" />

                    <motion.div
                        className="absolute bottom-36 right-12 bg-white text-gray-800 p-4 rounded-xl shadow-xl w-64 text-sm font-bold text-center"
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                    >
                        <p className="mb-2 text-[#5697B0] text-lg">가상 피팅 & 옷장</p>
                        여기서 AI 피팅을 시작하고<br />옷장을 관리하세요!👜
                    </motion.div>

                    <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 text-center z-20">
                        <h2 className="text-3xl font-bold text-white mb-4 drop-shadow-lg">
                            나만의 옷장
                        </h2>
                        <p className="text-white/90 text-xl font-medium drop-shadow-md leading-relaxed">
                            우측 하단 버튼을 눌러<br />시작해보세요!
                        </p>
                    </div>
                </div>
            )
        },
        // Step 5: 피팅 가이드 (공통)
        mobileSteps[4]
    ];

    const handleFinish = () => {
        // 튜토리얼 완료 처리
        // localStorage.setItem("hasSeenTutorial", "true"); // 이 부분은 로직에 따라 활성화
        router.push("/main");
    };

    const handleNext = () => {
        const steps = isDesktop ? desktopSteps : mobileSteps;
        if (step < steps.length - 1) {
            setStep(step + 1);
        } else {
            handleFinish();
        }
    };

    // 데스크톱용 렌더링 (Start Page 스타일)
    const renderDesktopContent = () => {
        const currentStep = step;
        const desktopContent = [
            {
                title: "Navigation",
                subtitle: "코디 탐색하기",
                desc: "화살표를 클릭하여\n다양한 코디를 만나보세요!",
            },
            {
                title: "Like & Save",
                subtitle: "좋아요 & 저장",
                desc: "마음에 드는 코디는\n하트 버튼으로 저장하세요.",
            },
            {
                title: "Details",
                subtitle: "상세 정보 확인",
                desc: "화면 우측에서\n착용 아이템 정보를 확인하세요.",
            },
            {
                title: "Closet",
                subtitle: "나만의 옷장",
                desc: "가상 피팅을 시작하고\n옷장을 관리해보세요.",
            },
            {
                title: "Virtual Fitting",
                subtitle: "가상 피팅 가이드",
                desc: "정확한 피팅을 위해\n전신 사진을 업로드해주세요.",
            }
        ];

        const content = desktopContent[step];

        return (
            <div
                className="relative min-h-[100dvh] flex items-center justify-center p-4 md:p-8 bg-cover bg-center bg-no-repeat"
                style={{ backgroundImage: "url('/images/start_bg.png')" }}
            >
                {/* 데스크톱 레이아웃 (Start Page Guide Card 스타일) */}
                <div className="w-[500px] h-[660px]">
                    <div
                        className="rounded-[10px] h-full p-10 flex flex-col backdrop-blur-3xl shadow-2xl border border-white/50 justify-between transition-all duration-500"
                        style={{ backgroundColor: "rgba(253, 249, 247, 0.9)" }}
                    >
                        {/* Background Decor - Massive Number */}
                        <div className="absolute top-0 right-0 p-4 overflow-hidden pointer-events-none select-none">
                            <span className="text-[180px] leading-none font-bold font-outfit text-black/[0.03] tracking-tighter -mr-10 -mt-10 block">
                                0{step + 1}
                            </span>
                        </div>

                        {/* Background Decor - Soft Gradient Blob */}
                        <div className={`absolute top-1/3 left-1/2 -translate-x-1/2 w-64 h-64 rounded-full bg-gradient-to-tr from-orange-100/60 to-rose-100/40 blur-3xl pointer-events-none transition-all duration-700 ${step % 2 === 0 ? 'scale-100 opacity-70' : 'scale-110 opacity-50'}`} />

                        {/* 상단 페이지 표시 - Minimal */}
                        <div className="flex justify-between items-start relative z-10">
                            <div className="h-1 w-10 bg-black rounded-full" />
                        </div>

                        {/* 메인 컨텐츠 영역 */}
                        <div className="flex-1 flex flex-col justify-center relative z-10 pl-4">
                            <div className="flex flex-col animate-fadeIn">
                                <h2 className="text-[56px] leading-[1.1] font-bold text-gray-900 font-outfit mb-6 tracking-tight">
                                    {content.title.split(' ')[0]}<br />
                                    <span className="text-gray-400">{content.title.split(' ').slice(1).join(' ')}</span>
                                </h2>
                                <h3 className="text-xl font-medium text-gray-800 mb-4 font-outfit">
                                    {content.subtitle}
                                </h3>
                                <p className="text-[16px] text-gray-600 font-manrope leading-relaxed max-w-[280px] mb-10 pl-1 border-l-2 border-gray-200 whitespace-pre-line">
                                    {content.desc}
                                </p>
                            </div>
                        </div>

                        {/* 하단 네비게이션 */}
                        <div className="flex items-center justify-between pt-6 border-t border-gray-200/30 relative z-10">
                            {/* Dots */}
                            <div className="flex gap-4">
                                {desktopContent.map((_, i) => (
                                    <div
                                        key={i}
                                        className={`transition-all duration-300 ${i === step ? "w-8 h-1.5 bg-black rounded-full" : "w-1.5 h-1.5 bg-gray-300 rounded-full"
                                            }`}
                                    />
                                ))}
                            </div>

                            {/* Control Buttons */}
                            <div className="flex gap-2">
                                {/* Next / Start Button */}
                                <button
                                    onClick={handleNext}
                                    className="w-fit px-6 py-2 bg-black text-white rounded-full flex items-center justify-center hover:bg-gray-800 hover:scale-105 transition-all shadow-lg text-sm font-bold gap-2 group"
                                >
                                    {step === desktopContent.length - 1 ? "Start Swell" : "Next"}
                                    <div className="w-5 h-5 rounded-full bg-white/20 flex items-center justify-center group-hover:bg-white/30 transition-colors">
                                        {step === desktopContent.length - 1 ? (
                                            <Check className="w-3 h-3 text-white" strokeWidth={3} />
                                        ) : (
                                            <svg width="10" height="10" viewBox="0 0 12 12" fill="none" xmlns="http://www.w3.org/2000/svg">
                                                <path d="M1 11L11 1M11 1H3M11 1V9" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                                            </svg>
                                        )}
                                    </div>
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        );
    };

    if (!mounted) return null;

    // 데스크톱 뷰
    if (isDesktop) {
        return renderDesktopContent();
    }

    // 모바일 뷰 (기존 유지)
    return (
        <div className="fixed inset-0 bg-gray-900 z-[9999] overflow-hidden">
            {/* 배경 이미지 (Step에 따라 변경) */}
            <div className="absolute inset-0 transition-opacity duration-300">
                <div
                    className={`absolute inset-0 bg-cover bg-center transition-opacity duration-500 ${step <= 2 ? 'opacity-100' : 'opacity-0'}`}
                    style={{ backgroundImage: "url('/images/tutorial_bg_main.png')" }}
                />
                <div
                    className={`absolute inset-0 bg-cover bg-center transition-opacity duration-500 ${step > 2 ? 'opacity-100' : 'opacity-0'}`}
                    style={{ backgroundImage: "url('/images/tutorial_bg_closet.png')" }}
                />
            </div>

            {/* 어두운 오버레이 */}
            <div className="absolute inset-0 bg-black/60" />

            {/* 컨텐츠 */}
            <div className="absolute inset-0 flex flex-col">
                {/* 상단 진행바 */}
                <div className="w-full flex gap-1 p-2 pt-[calc(3rem+env(safe-area-inset-top))] px-4 z-50">
                    {mobileSteps.map((_, i) => (
                        <div
                            key={i}
                            className={`h-1 flex-1 rounded-full transition-all duration-300 ${i <= step ? "bg-white" : "bg-white/20"
                                }`}
                        />
                    ))}
                </div>

                {/* 메인 Step 영역 */}
                <div className="flex-1 relative">
                    <AnimatePresence mode="wait">
                        <motion.div
                            key={step}
                            initial={{ opacity: 0, scale: 0.9 }}
                            animate={{ opacity: 1, scale: 1 }}
                            exit={{ opacity: 0, scale: 1.1 }}
                            transition={{ duration: 0.3 }}
                            className="absolute inset-0"
                        >
                            {mobileSteps[step].render()}
                        </motion.div>
                    </AnimatePresence>
                </div>

                {/* 하단 버튼 */}
                <div className="p-6 pb-[calc(3rem+env(safe-area-inset-bottom))] z-50">
                    <button
                        onClick={handleNext}
                        className="w-full py-4 bg-white text-gray-900 rounded-xl font-bold text-lg shadow-lg hover:scale-[1.02] active:scale-[0.98] transition-all"
                    >
                        {step === mobileSteps.length - 1 ? "시작하기" : "확인"}
                    </button>
                </div>
            </div>
        </div>
    );
}
