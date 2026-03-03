"use client";

import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import { getClosetItems, deleteClosetItem } from "@/lib/closet";
import { uploadProfilePhoto } from "@/lib/profile";
import { getMe, logout } from "@/lib/auth";
import { startFitting, pollFittingStatus, getFittingHistory } from "@/lib/fitting";
import { API_BASE_URL } from "@/lib/api";

import ItemSelector from "@/components/closet/ItemSelector";
import ProgressBar from "@/components/common/ProgressBar";
import type { ClosetItem } from "@/lib/closet";
import type { FittingCategory } from "@/lib/fitting";

// 카테고리 매핑 (한글 ↔ 영문)
const CATEGORY_MAP: Record<string, FittingCategory> = {
  "상의": "top",
  "하의": "bottom",
  "아우터": "outer",
};

const CATEGORY_MAP_REVERSE: Record<FittingCategory, string> = {
  "top": "상의",
  "bottom": "하의",
  "outer": "아우터",
};

export default function ClosetPage() {
  const router = useRouter();

  // 인증 상태
  const [loading, setLoading] = useState(true);
  const [userName, setUserName] = useState("User");

  // 옷장 데이터
  const [closetItems, setClosetItems] = useState<ClosetItem[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<string>("전체");

  // 가상 피팅 상태
  const [fittingSlots, setFittingSlots] = useState<{
    상의: number | null;
    하의: number | null;
    아우터: number | null;
  }>({
    상의: null,
    하의: null,
    아우터: null,
  });

  const [userPhoto, setUserPhoto] = useState<string | null>(null);
  const [fittingResult, setFittingResult] = useState<string | null>(null);
  const [fittingStatus, setFittingStatus] = useState<"idle" | "processing" | "completed">("idle");
  const [fittingProgress, setFittingProgress] = useState<string>("");
  const [progressValue, setProgressValue] = useState(0); // 0~100
  const [estimatedSeconds, setEstimatedSeconds] = useState<number>(0); // 예상 소요 시간 (초)
  const [llmMessage, setLlmMessage] = useState<string | null>(null);

  // Fake Progress Bar Logic
  useEffect(() => {
    let interval: NodeJS.Timeout;

    if (fittingStatus === "processing") {
      setProgressValue(0);

      // 예상 시간이 설정되지 않았으면 기본값 30초 (혹은 아이템 개수 기반 추정 불가 시)
      const duration = estimatedSeconds > 0 ? estimatedSeconds : 45;

      // 100ms마다 업데이트
      const updateInterval = 100;
      const totalSteps = (duration * 1000) / updateInterval;
      const increment = 90 / totalSteps; // 90%까지 도달

      let p = 0;
      interval = setInterval(() => {
        p += increment;
        if (p > 90) p = 90; // 최대 90%에서 대기
        setProgressValue(p);
      }, updateInterval);

    } else if (fittingStatus === "completed") {
      setProgressValue(100);
    } else {
      setProgressValue(0);
      setEstimatedSeconds(0);
    }

    return () => clearInterval(interval);
  }, [fittingStatus, estimatedSeconds]);

  // UI 상태
  const [showDropdown, setShowDropdown] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // 모바일 탭 상태 ('fitting' | 'items')
  const [activeTab, setActiveTab] = useState<'fitting' | 'items'>('fitting');

  // 모바일 아이템 오버레이 상태
  const [mobileSelectedItemId, setMobileSelectedItemId] = useState<number | null>(null);

  // 아이템 선택 모달 상태
  const [isSelectorOpen, setIsSelectorOpen] = useState(false);
  const [activeSlot, setActiveSlot] = useState<"상의" | "하의" | "아우터" | null>(null);

  const handleSlotClick = (slot: "상의" | "하의" | "아우터") => {
    setActiveSlot(slot);
    setIsSelectorOpen(true);
  };

  const handleSelectorSelect = (item: ClosetItem) => {
    if (!activeSlot) return;

    setFittingSlots(prev => ({
      ...prev,
      [activeSlot]: item.id
    }));

    // 피팅 완료 상태였다면 초기화 (바로 '피팅 확인하기' 활성화)
    if (fittingStatus === "completed") {
      setFittingStatus("idle");
      setFittingResult(null);
      setLlmMessage(null);
    }

    setIsSelectorOpen(false);
  };

  // 초기화
  useEffect(() => {
    const token = sessionStorage.getItem("token");
    if (!token) {
      router.push("/start");
      return;
    }

    const storedName = sessionStorage.getItem("userName");
    if (storedName) setUserName(storedName);

    // 0. 로컬 저장소에서 선택된 아이템 복원 (우선순위 낮음 - 실제 피팅 상태가 있으면 덮어씌워짐)
    const savedSlots = sessionStorage.getItem("fittingSlots");
    if (savedSlots) {
      try {
        setFittingSlots(JSON.parse(savedSlots));
      } catch (e) {
        console.error("Failed to parse saved fitting slots", e);
      }
    }

    loadClosetItems();

    // 1. 프로필 사진 및 사용자 이름 복원
    getMe().then((res) => {
      // 사용자 이름 업데이트 (세션에 없었을 경우 대비)
      if (res.data.user.name) {
        setUserName(res.data.user.name);
        sessionStorage.setItem("userName", res.data.user.name);
      }

      if (res.data.user.profileImageUrl) {
        // 백엔드 URL을 절대 경로로 변환
        const fullPhotoUrl = res.data.user.profileImageUrl.startsWith("http")
          ? res.data.user.profileImageUrl
          : `${API_BASE_URL}${res.data.user.profileImageUrl}`;
        setUserPhoto(fullPhotoUrl);
      }
    });

    // 2. 가상 피팅 상태 복원
    restoreFittingStatus();

    setLoading(false);
  }, [router]);

  // 피팅 아이템 변경 시 저장
  useEffect(() => {
    sessionStorage.setItem("fittingSlots", JSON.stringify(fittingSlots));
  }, [fittingSlots]);

  // 가상 피팅 상태 복원 함수
  const restoreFittingStatus = async () => {
    try {
      // 최신 1개만 조회
      const history = await getFittingHistory({ page: 1, limit: 1 });
      const latestFitting = history.data.fittings[0]; // 최신 피팅

      if (!latestFitting) return;

      if (latestFitting.status === "processing") {
        // 진행 중이면 상태 설정 후 폴링 시작
        setFittingStatus("processing");
        setFittingProgress("이전 작업을 계속 진행 중입니다...");

        // 진행 중인 아이템 슬롯에 복원
        if (latestFitting.items && latestFitting.items.length > 0) {
          const restoredSlots = { ...fittingSlots };
          latestFitting.items.forEach(item => {
            // item.category는 'top', 'bottom', 'outer' 형태이므로 한글로 변환
            const koreanCategory = CATEGORY_MAP_REVERSE[item.category as FittingCategory];
            if (koreanCategory) {
              restoredSlots[koreanCategory as "상의" | "하의" | "아우터"] = item.itemId;
            }
          });
          setFittingSlots(restoredSlots);

          // 복원 시 예상 시간 설정
          const count = latestFitting.items.length;
          setEstimatedSeconds(count * 15);
        }

        // 폴링 재개
        pollFittingStatus(latestFitting.jobId)
          .then((result) => {
            if (result.data.status === "completed") {
              setFittingResult(result.data.resultImageUrl || null);
              setLlmMessage(result.data.llmMessage || null);
              setFittingStatus("completed");
              setFittingProgress("");
            } else if (result.data.status === "failed") {
              // 조용히 실패 처리 (또는 알림)
              setFittingStatus("idle");
            } else if (result.data.status === "timeout") {
              setFittingStatus("idle");
            }
          })
          .catch(() => {
            setFittingStatus("idle");
          });

      } else if (latestFitting.status === "completed") {
        // 완료된 상태면 결과 표시
        setFittingResult(latestFitting.resultImageUrl);

        // 완료된 아이템 슬롯에 복원 (선택사항: 완료된 결과의 아이템을 보여줄지 여부)
        // 사용자가 "다시 피팅"을 누르기 전까지는 완료된 피팅의 아이템을 보여주는 것이 자연스러움
        if (latestFitting.items && latestFitting.items.length > 0) {
          const restoredSlots = { ...fittingSlots };
          latestFitting.items.forEach(item => {
            const koreanCategory = CATEGORY_MAP_REVERSE[item.category as FittingCategory];
            if (koreanCategory) {
              restoredSlots[koreanCategory as "상의" | "하의" | "아우터"] = item.itemId;
            }
          });
          setFittingSlots(restoredSlots);
        }
        // LLM 메시지는 history에 없으므로 (FittingHistoryItem 정의 확인 필요) 
        // 상세 조회 API를 호출하거나, history에 포함되어 있다면 사용.
        // 현재 FittingHistoryItem에는 llmMessage가 없으므로 상세 조회 필요할 수 있음.
        // 하지만 요구사항에는 "llmMessage 설절"이라고 되어 있음.
        // API 명세 상 getFittingHistory 반환값에 llmMessage가 있는지 확인했었나?
        // lib/fitting.ts FittingHistoryItem 에는 llmMessage가 없음.
        // 따라서 getFittingStatus(jobId)를 호출해서 가져오거나 해야 함.
        // 여기서는 상세 조회를 추가로 호출하여 확실하게 데이터를 가져오도록 개선.

        // 상세 정보 조회하여 LLM 메시지까지 복원
        // (import getFittingStatus 필요하지만 pollFittingStatus 내부적으로 사용하므로 
        //  pollFittingStatus를 불러도 되지만, 이미 완료된 건이라 바로 리턴될 것임)

        pollFittingStatus(latestFitting.jobId).then(result => {
          if (result.data.status === "completed") {
            setFittingResult(result.data.resultImageUrl || null);
            setLlmMessage(result.data.llmMessage || null);
            setFittingStatus("completed");
          }
        });
      }
      // failed/timeout은 무시 (idle 상태 유지)
    } catch (err) {
      console.error("피팅 상태 복원 실패:", err);
    }
  };

  // 드롭다운 외부 클릭 시 닫기
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setShowDropdown(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // 옷장 아이템 로드
  const loadClosetItems = async () => {
    try {
      const response = await getClosetItems({ category: "all", limit: 50 });
      setClosetItems(response.data.items);
    } catch (err) {
      const error = err as any;
      console.error("옷장 로딩 실패:", error);
      console.error("에러 메시지:", error.response?.data?.error?.message);
    }
  };

  // 카테고리 필터링
  const categories = ["전체", "상의", "하의", "아우터"];
  const filteredItems = selectedCategory === "전체"
    ? closetItems
    : closetItems.filter(item => {
      const koreanCategory = CATEGORY_MAP_REVERSE[item.category as FittingCategory];
      return koreanCategory === selectedCategory;
    });

  // 아이템 클릭 시 슬롯에 추가/제거
  const handleItemClick = (item: ClosetItem) => {
    const koreanCategory = CATEGORY_MAP_REVERSE[item.category as FittingCategory];
    if (!koreanCategory) return;

    const slotCategory = koreanCategory as "상의" | "하의" | "아우터";

    setFittingSlots(prev => ({
      ...prev,
      [slotCategory]: prev[slotCategory] === item.id ? null : item.id
    }));
  };

  // 슬롯에서 아이템 제거
  const handleRemoveFromSlot = (slotCategory: "상의" | "하의" | "아우터") => {
    setFittingSlots(prev => ({
      ...prev,
      [slotCategory]: null
    }));

    // 피팅 완료 상태였다면 초기화
    if (fittingStatus === "completed") {
      setFittingStatus("idle");
      setFittingResult(null);
      setLlmMessage(null);
    }
  };

  // 슬롯의 아이템 정보 가져오기
  const getSlotItem = (slotCategory: "상의" | "하의" | "아우터") => {
    const itemId = fittingSlots[slotCategory];
    return itemId ? closetItems.find(item => item.id === itemId) : null;
  };

  // 프로필 사진 업로드
  const handlePhotoUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    try {
      console.log("📤 업로드 시작:", file.name, file.type, file.size);
      const response = await uploadProfilePhoto(file);
      console.log("✅ 업로드 응답:", response);
      console.log("📷 photoUrl:", response.data.photoUrl);

      // 백엔드 URL을 절대 경로로 변환
      const fullPhotoUrl = response.data.photoUrl.startsWith("http")
        ? response.data.photoUrl
        : `${API_BASE_URL}${response.data.photoUrl}`;

      console.log("🌐 전체 URL:", fullPhotoUrl);

      setUserPhoto(fullPhotoUrl);
      setFittingResult(null);
      setFittingStatus("idle");
      alert("사진이 업로드되었습니다!");
    } catch (err) {
      const error = err as any;
      console.error("❌ 업로드 에러 전체:", error);
      console.error("❌ 에러 메시지:", error.message);
      console.error("❌ 에러 코드:", error.code);
      console.error("❌ 응답 데이터:", error.response?.data);
      console.error("❌ 응답 상태:", error.response?.status);

      const errorMessage = error.response?.data?.error?.message || error.message || "사진 업로드 실패";
      alert(`업로드 실패: ${errorMessage}`);
    }
  };

  // 가상 피팅 실행
  const handleFitting = async () => {
    const selectedItems = Object.entries(fittingSlots)
      .filter(([_, id]) => id !== null)
      .map(([koreanCat, id]) => ({
        itemId: id!,
        category: CATEGORY_MAP[koreanCat as "상의" | "하의" | "아우터"]
      }));

    if (selectedItems.length === 0) {
      alert("최소 1개 이상의 아이템을 선택해주세요");
      return;
    }

    // 피팅 소요 시간: 약 45초 고정 (사용자 요청 40-50초)
    const estimated = 45;
    setEstimatedSeconds(estimated);

    setFittingStatus("processing");
    setFittingProgress("피팅 시작 중...");

    try {
      // 1. 피팅 시작
      const startResponse = await startFitting({ items: selectedItems });
      const jobId = startResponse.data.jobId;

      setFittingProgress("멋진 사진 완성 중..");

      // 2. 상태 폴링
      const result = await pollFittingStatus(jobId);

      if (result.data.status === "completed") {
        setFittingResult(result.data.resultImageUrl || null);
        setLlmMessage(result.data.llmMessage || null);
        setFittingStatus("completed");
        setFittingProgress("");
        // 피팅 완료 시 큐 초기화
        setFittingSlots({
          상의: null,
          하의: null,
          아우터: null,
        });
      } else if (result.data.status === "failed") {
        alert(`피팅 실패: ${result.data.error || "알 수 없는 오류"}`);
        setFittingStatus("idle");
        setFittingProgress("");
      } else if (result.data.status === "timeout") {
        alert("피팅 처리 시간이 초과되었습니다. 다시 시도해주세요.");
        setFittingStatus("idle");
        setFittingProgress("");
      }
    } catch (err) {
      const error = err as any;
      console.error("피팅 실패:", error);
      alert(error.response?.data?.error?.message || "피팅 요청 실패");
      setFittingStatus("idle");
      setFittingProgress("");
    }
  };

  // 로그아웃

  const handleLogout = async () => {
    try {
      sessionStorage.removeItem("token");
      sessionStorage.removeItem("userName");
      sessionStorage.removeItem("fittingSlots");
      sessionStorage.removeItem("mainPageNavigating");
      localStorage.removeItem("mainPageToken"); // Also clear explicit token if possible

      await logout(); // Call API logout
      router.push("/start");
    } catch (_err) {
      router.push("/start");
    }
  };

  // 피팅 가능 여부 (사진 있고, 아이템 1개 이상 선택되고, 완료 상태가 아닐 때)
  const canFit = userPhoto && (fittingSlots.상의 || fittingSlots.하의 || fittingSlots.아우터) && fittingStatus !== "completed";

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gradient-to-b from-[rgba(86,151,176,0.45)] via-[rgba(255,244,234,0.65)] to-[rgba(255,244,234,1)]">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-[#5697B0] border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-gray-500">로딩 중...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-[100dvh] bg-gradient-to-b from-[rgba(86,151,176,0.45)] via-[rgba(255,244,234,0.65)] to-[rgba(255,244,234,1)] flex flex-col overflow-hidden">
      {/* 상단 네비게이션 */}
      <nav className="bg-transparent px-6 pb-4 pt-[calc(1rem+env(safe-area-inset-top))] flex justify-between items-center flex-shrink-0 w-full">
        {/* 모바일: Swell 로고 / 데스크톱: ← Main + 페이지 제목 */}
        <div className="flex items-center gap-4">
          {/* 데스크톱 전용 */}
          <button
            onClick={() => {
              sessionStorage.setItem("mainPageNavigating", "true");
              router.push("/main");
            }}
            className="hidden md:block text-gray-600 hover:text-gray-800 font-medium"
          >
            ← Main
          </button>
          <h1 className="hidden md:block text-xl font-bold text-gray-800">My Closet</h1>

          {/* 모바일 전용: Swell 로고 */}
          <h1
            className="md:hidden text-[20px] font-bold text-gray-900 flex items-center gap-2 cursor-pointer font-snippet"
            onClick={() => {
              sessionStorage.setItem("mainPageNavigating", "true");
              router.push("/main");
            }}
          >
            Swell
          </h1>
        </div>

        {/* 프로필 드롭다운 */}
        <div className="relative" ref={dropdownRef}>
          <button
            onClick={() => setShowDropdown(!showDropdown)}
            className="flex items-center gap-2 text-gray-600 hover:text-gray-800"
          >
            <span className="font-medium">{userName}</span>
            <span className={`transition-transform duration-200 ${showDropdown ? "rotate-180" : ""}`}>▼</span>
          </button>

          {showDropdown && (
            <div className="absolute right-0 mt-2 w-48 bg-white rounded-lg shadow-lg border py-2 z-50 animate-fadeIn">
              <button
                onClick={() => {
                  router.push("/favorites");
                  setShowDropdown(false);
                }}
                className="w-full px-4 py-2 text-left hover:bg-gray-50 flex items-center gap-2 text-[13px]"
              >
                ❤️ 좋아요한 코디
              </button>
              <button
                onClick={() => {
                  handleLogout();
                  setShowDropdown(false);
                }}
                className="w-full px-4 py-2 text-left hover:bg-gray-50 flex items-center gap-2 text-[13px]"
              >
                🚪 Logout
              </button>
            </div>
          )}
        </div>
      </nav>

      {/* 데스크톱: 기존 레이아웃 */}
      <div className="hidden md:flex flex-1 overflow-hidden">

        {/* 왼쪽: 가상 피팅 영역 */}
        <div className="w-[45%] p-6 flex">
          {/* 사진 영역 */}
          <div className="flex-1 flex flex-col">
            <div className="flex-1 bg-white rounded-2xl shadow-lg overflow-hidden relative">
              {fittingStatus === "processing" ? (
                // 피팅 진행 중
                <div className="h-full flex flex-col items-center justify-center p-8">
                  <video
                    src="/videos/logo_animation.mp4"
                    autoPlay
                    loop
                    muted
                    playsInline
                    className="w-64 h-64 object-contain mb-4"
                  />
                  <div className="w-full px-8 mb-2">
                    <ProgressBar progress={progressValue} />
                  </div>
                  <p className="text-gray-600 text-center font-medium">{fittingProgress}</p>
                  <p className="text-sm text-gray-400 mt-2">
                    잠시만 기다려주세요...
                    {estimatedSeconds > 0 && `(약 ${estimatedSeconds}초 소요 예정)`}
                  </p>
                </div>
              ) : fittingResult ? (
                // 피팅 결과
                <div className="h-full relative">
                  <img
                    src={fittingResult}
                    alt="피팅 결과"
                    className="w-full h-full object-contain"
                  />
                  <button
                    onClick={() => {
                      setFittingResult(null);
                      setLlmMessage(null);
                      setFittingStatus("idle");
                    }}
                    className="absolute top-4 right-4 px-4 py-2 bg-white/90 rounded-lg shadow hover:bg-white transition text-sm font-medium"
                  >
                    다시 피팅
                  </button>

                  {/* LLM 메시지 */}
                  {llmMessage && (
                    <div className="absolute bottom-4 left-4 right-4 bg-[#B7C9E2]/80 backdrop-blur-sm rounded-xl p-4 shadow-xl border border-white/20 animate-fadeIn">
                      <p className="text-black text-sm leading-relaxed font-medium">
                        💬 {llmMessage}
                      </p>
                    </div>
                  )}
                </div>
              ) : userPhoto ? (
                // 업로드된 사진
                <div className="h-full relative">
                  <img
                    src={userPhoto}
                    alt="내 사진"
                    className="w-full h-full object-contain"
                    onLoad={() => console.log("✅ 이미지 로드 성공:", userPhoto)}
                    onError={(e) => {
                      console.error("❌ 이미지 로드 실패:", userPhoto);
                      console.error("에러 상세:", e);
                    }}
                  />
                </div>
              ) : (
                // 업로드 영역
                <div
                  className="h-full flex flex-col items-center justify-center cursor-pointer hover:bg-gray-50 transition"
                  onClick={() => fileInputRef.current?.click()}
                >
                  <div className="text-6xl mb-4">📷</div>
                  <p className="text-gray-600 font-medium">사진을 업로드하세요</p>
                  <p className="text-sm text-gray-400 mt-2">클릭하여 파일 선택</p>
                </div>
              )}

              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                onChange={handlePhotoUpload}
                className="hidden"
              />
            </div>

            {/* 하단 버튼 영역 */}
            <div className="mt-4 flex gap-3">
              {userPhoto && (
                <button
                  onClick={() => fileInputRef.current?.click()}
                  className="px-6 py-3 border-2 border-gray-300 rounded-xl hover:bg-gray-50 transition font-medium"
                >
                  사진 변경
                </button>
              )}
              <button
                onClick={handleFitting}
                disabled={!canFit || fittingStatus === "processing"}
                className="flex-1 py-3 bg-[#5697B0] text-white rounded-xl font-medium hover:opacity-90 disabled:bg-gray-300 disabled:cursor-not-allowed transition"
              >
                {fittingStatus === "processing" ? "피팅 중..." : "피팅 확인하기"}
              </button>
            </div>
          </div>

          {/* 옷걸이 슬롯 */}
          <div className="w-[100px] ml-4 flex flex-col gap-3">
            <p className="text-sm font-medium text-gray-600 text-center"></p>

            {(["상의", "하의", "아우터"] as const).map((slotCategory) => (
              <div
                key={slotCategory}
                className="flex-1 bg-white rounded-xl shadow border-2 border-dashed border-gray-300 flex flex-col items-center justify-center p-2 relative"
              >
                <p className="text-xs text-gray-400 mb-1">{slotCategory}</p>
                {getSlotItem(slotCategory) ? (
                  <div className="relative w-full">
                    <div className="aspect-square bg-gray-100 rounded-lg overflow-hidden">
                      {getSlotItem(slotCategory)?.imageUrl ? (
                        <img
                          src={getSlotItem(slotCategory)!.imageUrl!}
                          alt={getSlotItem(slotCategory)?.name}
                          className="w-full h-full object-cover"
                        />
                      ) : (
                        <div className="w-full h-full flex items-center justify-center">
                          <span className="text-2xl">
                            {slotCategory === "상의" ? "👔" : slotCategory === "하의" ? "👖" : "🧥"}
                          </span>
                        </div>
                      )}
                    </div>
                    {/* 삭제 버튼을 이미지 컨테이너 밖으로 이동 */}
                    <button
                      onClick={() => handleRemoveFromSlot(slotCategory)}
                      className="absolute -top-1 -right-1 w-5 h-5 bg-red-500 text-white rounded-full text-xs flex items-center justify-center hover:bg-red-600 transition shadow-md"
                    >
                      ✕
                    </button>
                  </div>
                ) : (
                  <div className="aspect-square w-full bg-gray-50 rounded-lg flex items-center justify-center">
                    <span className="text-gray-300 text-2xl">+</span>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* 오른쪽: 옷장 아이템 목록 */}
        <div className="w-[55%] bg-transparent p-6 flex flex-col overflow-hidden">
          {/* 카테고리 필터 */}
          <div className="flex flex-wrap gap-2 mb-4 flex-shrink-0">
            {categories.map((category) => (
              <button
                key={category}
                onClick={() => setSelectedCategory(category)}
                className={`px-4 py-2 rounded-full text-sm font-medium transition-all ${selectedCategory === category
                  ? "bg-[#5697B0] text-white"
                  : "bg-white text-gray-600 hover:bg-gray-50 border border-gray-200"
                  }`}
              >
                {category}
              </button>
            ))}
          </div>

          {/* 아이템 그리드 */}
          <div className="flex-1 overflow-auto p-1">
            <div className="grid grid-cols-4 gap-3">
              {filteredItems.map((item) => {
                const koreanCategory = CATEGORY_MAP_REVERSE[item.category as FittingCategory];
                const isInSlot =
                  fittingSlots.상의 === item.id ||
                  fittingSlots.하의 === item.id ||
                  fittingSlots.아우터 === item.id;

                return (
                  <div
                    key={item.id}
                    className={`bg-white rounded-xl p-3 transition-all group relative ${isInSlot
                      ? "ring-2 ring-[#5697B0] bg-blue-50"
                      : "hover:shadow-lg"
                      }`}
                  >
                    {/* 아이템 이미지 */}
                    <div className="aspect-square bg-gray-50 rounded-lg mb-2 flex items-center justify-center relative overflow-hidden">
                      {item.imageUrl ? (
                        <img src={item.imageUrl} alt={item.name} className="w-full h-full object-cover" />
                      ) : (
                        <span className="text-3xl">
                          {koreanCategory === "상의" ? "👔" : koreanCategory === "하의" ? "👖" : "🧥"}
                        </span>
                      )}

                      {/* Hover 오버레이 */}
                      <div className="absolute inset-0 bg-black/70 opacity-0 group-hover:opacity-100 transition-opacity flex flex-col items-center justify-center gap-2 p-2">
                        {/* 삭제 버튼 (왼쪽 상단) */}
                        <button
                          onClick={async (e) => {
                            e.stopPropagation();
                            if (confirm('이 아이템을 옷장에서 삭제하시겠습니까?')) {
                              try {
                                await deleteClosetItem(item.id);
                                await loadClosetItems();
                                alert('삭제되었습니다');
                              } catch (err) {
                                const error = err as any;
                                alert(error.response?.data?.error?.message || '삭제 실패');
                              }
                            }
                          }}
                          className="absolute top-2 left-2 w-6 h-6 bg-red-500 text-white rounded-full flex items-center justify-center hover:bg-red-600 transition text-xs font-bold"
                        >
                          ✕
                        </button>

                        {/* 피팅에 추가 버튼 */}
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleItemClick(item);
                          }}
                          className="w-full px-3 py-2 bg-[#5697B0] text-white rounded-lg text-xs font-medium hover:bg-[#4a8299] transition"
                        >
                          {isInSlot ? '피팅에서 제거' : '피팅에 추가'}
                        </button>

                        {/* 구매 링크 방문 버튼 */}
                        {item.purchaseUrl && (
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              if (item.purchaseUrl) {
                                window.open(item.purchaseUrl, '_blank');
                              }
                            }}
                            className="w-full px-3 py-2 bg-white text-gray-800 rounded-lg text-xs font-medium hover:bg-gray-100 transition"
                          >
                            구매 링크 방문
                          </button>
                        )}
                      </div>

                      {isInSlot && (
                        <div className="absolute top-1 right-1 w-6 h-6 bg-[#5697B0] rounded-full flex items-center justify-center text-white text-xs">
                          ✓
                        </div>
                      )}
                    </div>

                    {/* 아이템 정보 */}
                    <p className="text-xs text-gray-400">{item.brand || "BRAND"}</p>
                    <p className="font-medium text-gray-800 text-sm truncate">{item.name}</p>
                    {item.price && (
                      <p className="text-[#5697B0] font-bold text-sm mt-1">
                        {item.price.toLocaleString()}원
                      </p>
                    )}
                  </div>
                );
              })}
            </div>

            {filteredItems.length === 0 && (
              <div className="flex items-center justify-center h-40 text-gray-400">
                <div className="text-center">
                  <p className="text-5xl mb-2">📦</p>
                  <p>이 카테고리에 저장된 아이템이 없어요</p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* 모바일: 탭 기반 레이아웃 */}
      <div className="md:hidden flex-1 flex flex-col overflow-hidden pb-[calc(3.5rem+env(safe-area-inset-bottom))]">
        {/* 탭 헤더 */}
        <div className="flex border-b border-gray-200 bg-transparent backdrop-blur-sm flex-shrink-0">
          <button
            onClick={() => setActiveTab('fitting')}
            className={`flex-1 py-3 text-sm font-medium transition-all ${activeTab === 'fitting'
              ? 'text-[#5697B0] border-b-2 border-[#5697B0]'
              : 'text-gray-500'
              }`}
          >
            가상 피팅
          </button>
          <button
            onClick={() => setActiveTab('items')}
            className={`flex-1 py-3 text-sm font-medium transition-all ${activeTab === 'items'
              ? 'text-[#5697B0] border-b-2 border-[#5697B0]'
              : 'text-gray-500'
              }`}
          >
            아이템 목록
          </button>
        </div>

        {/* 피팅 탭 */}
        {activeTab === 'fitting' && (
          <div className="flex-1 flex flex-col p-4 overflow-auto">
            {/* 사진 영역 - 더 크게 */}
            <div className="bg-white rounded-2xl shadow-lg overflow-hidden relative mb-3 min-h-[400px]">
              {fittingStatus === "processing" ? (
                <div className="h-full flex flex-col items-center justify-center p-8 min-h-[400px]">
                  <video
                    src="/videos/logo_animation.mp4"
                    autoPlay
                    loop
                    muted
                    playsInline
                    className="w-32 h-32 object-contain mb-4"
                  />
                  <div className="w-full px-8 mb-2">
                    <ProgressBar progress={progressValue} />
                  </div>
                  <p className="text-gray-600 text-center font-medium text-sm">{fittingProgress}</p>
                  <p className="text-xs text-gray-400 mt-2">
                    잠시만 기다려주세요...
                    {estimatedSeconds > 0 && `(약 ${estimatedSeconds}초 소요 예정)`}
                  </p>
                </div>
              ) : fittingResult ? (
                <div className="relative w-full">
                  <img
                    src={fittingResult}
                    alt="피팅 결과"
                    className="w-full h-auto object-contain max-h-[70vh]"
                  />
                  <button
                    onClick={() => {
                      setFittingResult(null);
                      setLlmMessage(null);
                      setFittingStatus("idle");
                    }}
                    className="absolute top-3 right-3 px-3 py-1.5 bg-white/90 rounded-lg shadow hover:bg-white transition text-xs font-medium"
                  >
                    다시 피팅
                  </button>

                </div>
              ) : userPhoto ? (
                <div className="relative w-full">
                  <img
                    src={userPhoto}
                    alt="내 사진"
                    className="w-full h-auto object-contain max-h-[70vh]"
                  />
                </div>
              ) : (
                <div
                  className="flex flex-col items-center justify-center cursor-pointer hover:bg-gray-50 transition min-h-[400px]"
                  onClick={() => fileInputRef.current?.click()}
                >
                  <div className="text-5xl mb-3">📷</div>
                  <p className="text-gray-600 font-medium text-sm">사진을 업로드하세요</p>
                  <p className="text-xs text-gray-400 mt-1">클릭하여 파일 선택</p>
                </div>
              )}

              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                onChange={handlePhotoUpload}
                className="hidden"
              />
            </div>

            {/* LLM 메시지 (모바일: 이미지 하단으로 이동 - 잘림 방지) */}
            {fittingResult && llmMessage && (
              <div className="bg-[#B7C9E2] rounded-xl p-4 shadow-md border border-white/20 mb-3 animate-fadeIn">
                <p className="text-gray-800 text-sm leading-relaxed font-medium">
                  💬 {llmMessage}
                </p>
              </div>
            )}

            {/* 옷걸이 슬롯 (가로 3개) - 더 작게 */}
            <div className="flex gap-2 mb-3">
              {(["상의", "하의", "아우터"] as const).map((slotCategory) => (
                <div
                  key={slotCategory}
                  onClick={() => handleSlotClick(slotCategory)}
                  className="flex-1 bg-white rounded-lg shadow border border-dashed border-gray-300 p-1.5 relative cursor-pointer active:scale-95 transition-transform"
                >
                  <p className="text-[9px] text-gray-400 text-center mb-0.5">{slotCategory}</p>
                  {getSlotItem(slotCategory) ? (
                    <div className="relative">
                      <div className="aspect-square bg-gray-100 rounded-lg overflow-hidden">
                        {getSlotItem(slotCategory)?.imageUrl ? (
                          <img
                            src={getSlotItem(slotCategory)!.imageUrl!}
                            alt={getSlotItem(slotCategory)?.name}
                            className="w-full h-full object-cover"
                          />
                        ) : (
                          <div className="w-full h-full flex items-center justify-center">
                            <span className="text-2xl">
                              {slotCategory === "상의" ? "👔" : slotCategory === "하의" ? "👖" : "🧥"}
                            </span>
                          </div>
                        )}
                      </div>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleRemoveFromSlot(slotCategory);
                        }}
                        className="absolute -top-1 -right-1 w-5 h-5 bg-red-500 text-white rounded-full text-xs flex items-center justify-center hover:bg-red-600 transition shadow-md"
                      >
                        ✕
                      </button>
                    </div>
                  ) : (
                    <div className="aspect-square bg-gray-50 rounded-lg flex items-center justify-center">
                      <span className="text-gray-300 text-xl">+</span>
                    </div>
                  )}
                </div>
              ))}
            </div>

            {/* 버튼 영역 */}
            <div className="flex gap-2">
              {userPhoto && (
                <button
                  onClick={() => fileInputRef.current?.click()}
                  className="px-4 py-2.5 border-2 border-gray-300 rounded-xl hover:bg-gray-50 transition font-medium text-sm"
                >
                  사진 변경
                </button>
              )}
              <button
                onClick={handleFitting}
                disabled={!canFit || fittingStatus === "processing"}
                className="flex-1 py-2.5 bg-[#5697B0] text-white rounded-xl font-medium hover:opacity-90 disabled:bg-gray-300 disabled:cursor-not-allowed transition text-sm"
              >
                {fittingStatus === "processing" ? "피팅 중..." : "피팅 확인하기"}
              </button>
            </div>

            {/* 아이템 선택 모달 - 이동됨 */}
          </div>
        )}

        {/* 아이템 탭 */}
        {activeTab === 'items' && (
          <div className="flex-1 flex flex-col overflow-hidden">
            {/* 카테고리 필터 */}
            <div className="flex flex-wrap gap-2 p-4 pb-3 flex-shrink-0">
              {categories.map((category) => (
                <button
                  key={category}
                  onClick={() => setSelectedCategory(category)}
                  className={`px-3 py-1.5 rounded-full text-xs font-medium transition-all ${selectedCategory === category
                    ? "bg-[#5697B0] text-white"
                    : "bg-white text-gray-600 hover:bg-gray-50 border border-gray-200"
                    }`}
                >
                  {category}
                </button>
              ))}
            </div>

            {/* 아이템 그리드 (2열) */}
            <div className="flex-1 overflow-auto px-4 pb-4">
              <div className="grid grid-cols-2 gap-3">
                {filteredItems.map((item) => {
                  const koreanCategory = CATEGORY_MAP_REVERSE[item.category as FittingCategory];
                  const isInSlot =
                    fittingSlots.상의 === item.id ||
                    fittingSlots.하의 === item.id ||
                    fittingSlots.아우터 === item.id;

                  return (
                    <div
                      key={item.id}
                      onClick={() => setMobileSelectedItemId(mobileSelectedItemId === item.id ? null : item.id)}
                      className={`bg-white rounded-xl p-2.5 transition-all ${isInSlot
                        ? "ring-2 ring-[#5697B0] bg-blue-50"
                        : "shadow hover:shadow-md"
                        }`}
                    >
                      {/* 아이템 이미지 */}
                      <div className="aspect-square bg-gray-50 rounded-lg mb-2 flex items-center justify-center relative overflow-hidden">
                        {item.imageUrl ? (
                          <img src={item.imageUrl} alt={item.name} className="w-full h-full object-cover" />
                        ) : (
                          <span className="text-3xl">
                            {koreanCategory === "상의" ? "👔" : koreanCategory === "하의" ? "👖" : "🧥"}
                          </span>
                        )}

                        {/* 모바일 오버레이 */}
                        {mobileSelectedItemId === item.id && (
                          <div className="absolute inset-0 bg-black/70 flex flex-col items-center justify-center gap-2 p-2 animate-fadeIn">
                            {/* 피팅에 추가/제거 버튼 */}
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                handleItemClick(item);
                                setMobileSelectedItemId(null);
                              }}
                              className="w-full px-3 py-2 bg-[#5697B0] text-white rounded-lg text-xs font-medium hover:bg-[#4a8299] transition"
                            >
                              {isInSlot ? '피팅에서 제거' : '피팅에 추가'}
                            </button>

                            {/* 구매 링크 방문 버튼 */}
                            {item.purchaseUrl && (
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  if (item.purchaseUrl) {
                                    window.open(item.purchaseUrl, '_blank');
                                  }
                                  setMobileSelectedItemId(null);
                                }}
                                className="w-full px-3 py-2 bg-white text-gray-800 rounded-lg text-xs font-medium hover:bg-gray-100 transition"
                              >
                                구매 링크 방문
                              </button>
                            )}
                          </div>
                        )}

                        {isInSlot && mobileSelectedItemId !== item.id && (
                          <div className="absolute top-1 right-1 w-6 h-6 bg-[#5697B0] rounded-full flex items-center justify-center text-white text-xs">
                            ✓
                          </div>
                        )}
                      </div>

                      {/* 아이템 정보 */}
                      <p className="text-[10px] text-gray-400 mb-0.5">{item.brand || "BRAND"}</p>
                      <p className="font-medium text-gray-800 text-xs truncate leading-tight">{item.name}</p>
                      {item.price && (
                        <p className="text-[#5697B0] font-bold text-xs mt-1">
                          {item.price.toLocaleString()}원
                        </p>
                      )}
                    </div>
                  );
                })}
              </div>

              {filteredItems.length === 0 && (
                <div className="flex items-center justify-center h-40 text-gray-400">
                  <div className="text-center">
                    <p className="text-4xl mb-2">📦</p>
                    <p className="text-sm">이 카테고리에 저장된 아이템이 없어요</p>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>



      {/* 아이템 선택 모달 (전역 배치) */}
      <ItemSelector
        isOpen={isSelectorOpen}
        onClose={() => setIsSelectorOpen(false)}
        category={activeSlot || ""}
        items={closetItems.filter(item => {
          if (!activeSlot) return false;
          const itemKoreanCategory = CATEGORY_MAP_REVERSE[item.category as FittingCategory];
          return itemKoreanCategory === activeSlot;
        })}
        onSelect={handleSelectorSelect}
      />
    </div>
  );
}