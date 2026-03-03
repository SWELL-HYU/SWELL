"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { getPreferenceOptions, setPreferences } from "@/lib/onboarding";
import type { Tag, SampleOutfit } from "@/lib/onboarding";

export default function OnboardingPage() {
  const router = useRouter();
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // 상태 관리
  const [step, setStep] = useState<1 | 2>(1); // 1: 태그 선택, 2: 코디 선택
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [isAnimating, setIsAnimating] = useState(true);

  // 데이터
  const [tags, setTags] = useState<Tag[]>([]);
  const [outfits, setOutfits] = useState<SampleOutfit[]>([]);

  // 선택한 항목
  const [selectedTags, setSelectedTags] = useState<number[]>([]);
  const [selectedOutfits, setSelectedOutfits] = useState<number[]>([]);

  // 초기 데이터 로드
  useEffect(() => {
    const token = sessionStorage.getItem("token");
    if (!token) {
      router.push("/start");
      return;
    }

    loadOptions();
  }, [router]);

  // 애니메이션 완료 후 상태 업데이트
  useEffect(() => {
    const timer = setTimeout(() => {
      setIsAnimating(false);
    }, 600);
    return () => clearTimeout(timer);
  }, []);

  const loadOptions = async () => {
    setLoading(true);
    setError("");

    try {
      const response = await getPreferenceOptions();
      setTags(response.data.hashtags);
      setOutfits(response.data.sampleOutfits);
    } catch (err: any) {
      console.error("옵션 로딩 실패:", err);
      setError("데이터를 불러오는데 실패했습니다");
    } finally {
      setLoading(false);
    }
  };

  // 태그 선택/해제
  const toggleTag = (tagId: number) => {
    if (selectedTags.includes(tagId)) {
      setSelectedTags(selectedTags.filter((id) => id !== tagId));
    } else {
      if (selectedTags.length >= 10) {
        alert("최대 10개까지 선택할 수 있습니다");
        return;
      }
      setSelectedTags([...selectedTags, tagId]);
    }
  };

  // 코디 선택/해제
  const toggleOutfit = (outfitId: number) => {
    if (selectedOutfits.includes(outfitId)) {
      setSelectedOutfits(selectedOutfits.filter((id) => id !== outfitId));
    } else {
      if (selectedOutfits.length >= 5) {
        alert("최대 5개까지 선택할 수 있습니다");
        return;
      }
      setSelectedOutfits([...selectedOutfits, outfitId]);
    }
  };

  // 다음 단계로
  const handleNext = () => {
    if (selectedTags.length < 3) {
      alert("최소 3개의 태그를 선택해주세요");
      return;
    }
    setStep(2);
  };

  // 이전 단계로
  const handleBack = () => {
    setStep(1);
  };

  // 스크롤 함수
  const scroll = (direction: 'left' | 'right') => {
    if (scrollContainerRef.current) {
      const scrollAmount = 250; // 스크롤 거리
      scrollContainerRef.current.scrollBy({
        left: direction === 'left' ? -scrollAmount : scrollAmount,
        behavior: 'smooth'
      });
    }
  };

  // 제출
  const handleSubmit = async () => {
    if (selectedOutfits.length < 1) {
      alert("최소 1개의 코디를 선택해주세요");
      return;
    }

    setSubmitting(true);

    try {
      await setPreferences({
        hashtagIds: selectedTags,
        sampleOutfitIds: selectedOutfits,
      });

      // 성공 시 튜토리얼 페이지로
      router.push("/tutorial");
    } catch (err: any) {
      console.error("선호도 저장 실패:", err);
      const errorMessage = err.response?.data?.error?.message || "저장에 실패했습니다";
      alert(errorMessage);
      setSubmitting(false);
    }
  };

  // 로딩 상태
  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-[rgba(86,151,176,0.45)] via-[rgba(255,244,234,0.65)] to-[rgba(255,244,234,1)] flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-[#5697B0] border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-gray-500">로딩 중...</p>
        </div>
      </div>
    );
  }

  // 에러 상태
  if (error && tags.length === 0) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-[rgba(86,151,176,0.45)] via-[rgba(255,244,234,0.65)] to-[rgba(255,244,234,1)] flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-500 mb-4">{error}</p>
          <button
            onClick={loadOptions}
            className="px-6 py-2 bg-[#5697B0] text-white rounded-lg hover:opacity-80"
          >
            다시 시도
          </button>
        </div>
      </div>
    );
  }

  return (
    <div
      className="relative min-h-screen flex items-center justify-center p-8 bg-cover bg-center bg-no-repeat"
      style={{ backgroundImage: "url('/images/start_bg.png')" }}
    >
      <style>{`
        @keyframes expandWidth {
          from {
            width: 500px;
            opacity: 0.8;
          }
          to {
            width: 1000px;
            opacity: 1;
          }
        }
        .onboarding-container {
          animation: expandWidth 0.6s ease-out forwards;
        }
      `}</style>

      {/* 데스크톱 레이아웃 */}
      <div
        ref={containerRef}
        className={`hidden md:flex h-[660px] rounded-[10px] flex-col overflow-y-auto ${isAnimating ? 'onboarding-container' : 'w-[1000px]'} bg-white/85 backdrop-blur-xl shadow-2xl border border-white/40`}
      >
        <div className="p-8 flex flex-col h-full">

          {/* 단계 표시 */}
          <div className="flex items-center justify-center mb-8">
            <div className="flex items-center gap-4">
              <div className={`w-10 h-10 rounded-full flex items-center justify-center text-sm font-bold ${step === 1 ? "bg-[#5697B0] text-white" : "bg-gray-200 text-gray-600"
                }`}>
                1
              </div>
              <div className="w-12 h-0.5 bg-gray-300"></div>
              <div className={`w-10 h-10 rounded-full flex items-center justify-center text-sm font-bold ${step === 2 ? "bg-[#5697B0] text-white" : "bg-gray-200 text-gray-600"
                }`}>
                2
              </div>
            </div>
          </div>

          {/* 1단계: 태그 선택 */}
          {step === 1 && (
            <div className="flex flex-col h-full">
              <div className="flex-shrink-0 mb-4">
                <h2 className="text-xl font-bold text-gray-900 mb-1 text-center">
                  어떤 스타일을 선호하시나요?
                </h2>
                <p className="text-xs text-gray-500 text-center mb-2">
                  최소 3개, 최대 10개의 헤시테그를 골라주세요
                </p>

                {/* 선택 카운터 */}
                <div className="text-center">
                  <span className={`text-sm font-bold ${selectedTags.length >= 3 ? "text-[#5697B0]" : "text-gray-400"
                    }`}>
                    {selectedTags.length}
                  </span>
                  <span className="text-xs text-gray-500"> / 10개</span>
                </div>
              </div>

              {/* 태그 버튼들 */}
              <div className="flex-1 flex flex-wrap gap-3 justify-center content-center">
                {tags.map((tag) => (
                  <button
                    key={tag.id}
                    onClick={() => toggleTag(tag.id)}
                    className={`px-6 py-3 rounded-full text-sm font-medium transition-all ${selectedTags.includes(tag.id)
                      ? "bg-[#5697B0]/20 text-[#2c5261] ring-2 ring-[#5697B0]"
                      : "bg-white text-gray-600 border-2 border-gray-200 hover:border-[#5697B0]/50"
                      }`}
                  >
                    {tag.name}
                  </button>
                ))}
              </div>

              {/* 다음 버튼 */}
              <button
                onClick={handleNext}
                disabled={selectedTags.length < 3}
                className="flex-shrink-0 w-full py-2 mt-4 bg-[#5697B0] text-white rounded-lg text-sm font-medium hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
              >
                다음 단계
              </button>
            </div>
          )}

          {/* 2단계: 코디 선택 */}
          {step === 2 && (
            <div className="flex flex-col h-full">
              <div className="flex-shrink-0 mb-3">
                <h2 className="text-xl font-bold text-gray-900 mb-1 text-center">
                  마음에 드는 코디를 골라보세요
                </h2>
                <p className="text-xs text-gray-500 text-center mb-2">
                  최소 1개, 최대 5개의 코디를 선택해주세요
                </p>

                {/* 선택 카운터 */}
                <div className="text-center">
                  <span className={`text-sm font-bold ${selectedOutfits.length >= 1 ? "text-[#5697B0]" : "text-gray-400"
                    }`}>
                    {selectedOutfits.length}
                  </span>
                  <span className="text-xs text-gray-500"> / 5개</span>
                </div>
              </div>

              {/* 코디 가로 스크롤 */}
              <div className="flex-1 flex flex-col justify-center mb-3 relative">
                {/* 왼쪽 화살표 */}
                <button
                  onClick={() => scroll('left')}
                  className="absolute left-0 top-1/2 -translate-y-1/2 z-10 w-10 h-10 rounded-full bg-black/50 hover:bg-black/70 text-white flex items-center justify-center transition-all"
                >
                  ‹
                </button>

                <div
                  ref={scrollContainerRef}
                  className="flex gap-4 overflow-x-auto pb-4 px-12 scroll-smooth"
                >
                  {outfits.map((outfit) => (
                    <button
                      key={outfit.id}
                      onClick={() => toggleOutfit(outfit.id)}
                      className="relative flex-shrink-0 w-48 aspect-[3/4] rounded-lg overflow-hidden border transition-all shadow-md hover:shadow-lg hover:scale-105"
                      style={{
                        borderColor: selectedOutfits.includes(outfit.id) ? "#5697B0" : "#e5e7eb"
                      }}
                    >
                      {/* 코디 이미지 */}
                      <img
                        src={outfit.imageUrl}
                        alt={`코디 ${outfit.id}`}
                        className="w-full h-full object-cover"
                      />

                      {/* 선택 체크마크 */}
                      {selectedOutfits.includes(outfit.id) && (
                        <div className="absolute inset-0 bg-[#5697B0]/20 flex items-center justify-center">
                          <div className="w-12 h-12 bg-[#5697B0] rounded-full flex items-center justify-center">
                            <span className="text-white text-2xl">✓</span>
                          </div>
                        </div>
                      )}
                    </button>
                  ))}
                </div>

                {/* 오른쪽 화살표 */}
                <button
                  onClick={() => scroll('right')}
                  className="absolute right-0 top-1/2 -translate-y-1/2 z-10 w-10 h-10 rounded-full bg-black/50 hover:bg-black/70 text-white flex items-center justify-center transition-all"
                >
                  ›
                </button>
              </div>

              {/* 버튼들 */}
              <div className="flex-shrink-0 flex gap-3">
                <button
                  onClick={handleBack}
                  className="flex-1 py-2 bg-gray-200 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-300 transition-all"
                >
                  이전
                </button>
                <button
                  onClick={handleSubmit}
                  disabled={selectedOutfits.length < 1 || submitting}
                  className="flex-1 py-2 bg-[#5697B0] text-white rounded-lg text-sm font-medium hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                >
                  {submitting ? "저장 중..." : "완료"}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* 모바일 레이아웃 */}
      <div className="md:hidden absolute inset-0 flex flex-col justify-center px-6">
        <div
          className="w-full max-w-[340px] mx-auto animate-fadeIn flex-col rounded-[10px] max-h-[80vh] overflow-hidden flex bg-white/85 backdrop-blur-xl shadow-2xl border border-white/40"
        >
          <div className="p-6 flex flex-col flex-1 min-h-0">
            {/* 단계 표시 (오리지널 스타일 복원) */}
            <div className="flex items-center justify-center mb-6 flex-shrink-0">
              <div className="flex items-center gap-3">
                <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold ${step === 1 ? "bg-[#5697B0] text-white" : "bg-gray-200 text-gray-600"
                  }`}>
                  1
                </div>
                <div className="w-8 h-0.5 bg-gray-300"></div>
                <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold ${step === 2 ? "bg-[#5697B0] text-white" : "bg-gray-200 text-gray-600"
                  }`}>
                  2
                </div>
              </div>
            </div>

            {step === 1 ? (
              <div className="flex flex-col flex-1 min-h-0">
                <div className="flex-shrink-0 mb-4 text-center">
                  <h2 className="text-[18px] font-bold text-gray-900 mb-1">
                    어떤 스타일을 선호하시나요?
                  </h2>
                  <p className="text-[11px] text-gray-600 mb-2">
                    최소 3개, 최대 10개의 헤시테그를 골라주세요
                  </p>
                  <div className="text-center">
                    <span className={`text-xs font-bold ${selectedTags.length >= 3 ? "text-[#5697B0]" : "text-gray-500"
                      }`}>
                      {selectedTags.length}
                    </span>
                    <span className="text-[10px] text-gray-500"> / 10개</span>
                  </div>
                </div>

                <div className="flex-1 flex flex-wrap gap-2 justify-center content-start overflow-y-auto pb-4 min-h-0">
                  {tags.map((tag) => (
                    <button
                      key={tag.id}
                      onClick={() => toggleTag(tag.id)}
                      className={`px-3 py-1.5 rounded-full text-[11px] font-medium transition-all ${selectedTags.includes(tag.id)
                        ? "bg-[#5697B0]/20 text-[#2c5261] ring-1 ring-[#5697B0]"
                        : "bg-white text-gray-600 border border-gray-200"
                        }`}
                    >
                      {tag.name}
                    </button>
                  ))}
                </div>

                <button
                  onClick={handleNext}
                  disabled={selectedTags.length < 3}
                  className="flex-shrink-0 w-full py-2.5 bg-[#5697B0] text-white rounded-lg text-sm font-medium hover:opacity-90 disabled:opacity-50 transition-all mt-2"
                >
                  다음 단계
                </button>
              </div>
            ) : (
              <div className="flex flex-col flex-1 min-h-0">
                <div className="flex-shrink-0 mb-3 text-center">
                  <h2 className="text-[18px] font-bold text-gray-900 mb-1">
                    마음에 드는 코디를 골라보세요
                  </h2>
                  <p className="text-[11px] text-gray-600 mb-2">
                    최소 1개, 최대 5개의 코디를 선택해주세요
                  </p>
                  <div className="text-center">
                    <span className={`text-xs font-bold ${selectedOutfits.length >= 1 ? "text-[#5697B0]" : "text-gray-500"
                      }`}>
                      {selectedOutfits.length}
                    </span>
                    <span className="text-[10px] text-gray-500"> / 5개</span>
                  </div>
                </div>

                <div className="flex-1 overflow-y-auto min-h-0 -mx-2 px-2">
                  <div className="grid grid-cols-2 gap-2 pb-2">
                    {outfits.map((outfit) => (
                      <button
                        key={outfit.id}
                        onClick={() => toggleOutfit(outfit.id)}
                        className="relative w-full aspect-[3/4] rounded-lg overflow-hidden border transition-all shadow-md hover:shadow-lg"
                        style={{
                          borderColor: selectedOutfits.includes(outfit.id) ? "#5697B0" : "#e5e7eb"
                        }}
                      >
                        <img
                          src={outfit.imageUrl}
                          alt={`코디 ${outfit.id}`}
                          className="w-full h-full object-cover"
                        />
                        {selectedOutfits.includes(outfit.id) && (
                          <div className="absolute inset-0 bg-[#5697B0]/20 flex items-center justify-center">
                            <div className="w-8 h-8 bg-[#5697B0] rounded-full flex items-center justify-center">
                              <span className="text-white text-sm">✓</span>
                            </div>
                          </div>
                        )}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="flex-shrink-0 flex gap-2 mt-3">
                  <button
                    onClick={handleBack}
                    className="flex-1 py-2 bg-gray-200 text-gray-700 rounded-lg text-xs font-medium hover:bg-gray-300 transition-all"
                  >
                    이전
                  </button>
                  <button
                    onClick={handleSubmit}
                    disabled={selectedOutfits.length < 1 || submitting}
                    className="flex-1 py-2 bg-[#5697B0] text-white rounded-lg text-xs font-medium hover:opacity-90 disabled:opacity-50 transition-all"
                  >
                    {submitting ? "저장 중..." : "완료"}
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>

  );
}