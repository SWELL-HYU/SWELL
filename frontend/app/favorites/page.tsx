"use client";

import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import { getFavorites, removeFavorite } from "@/lib/outfits";
import { saveClosetItem } from "@/lib/closet";
import { logout, getMe } from "@/lib/auth";
import HeartIcon from "@/components/common/HeartIcon";

import type { Outfit } from "@/types/api";

export default function FavoritesPage() {
  const router = useRouter();

  // 상태 관리
  const [favorites, setFavorites] = useState<Outfit[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showDropdown, setShowDropdown] = useState(false);
  const [userName, setUserName] = useState("User");

  // 모달 상태
  const [selectedOutfit, setSelectedOutfit] = useState<Outfit | null>(null);
  const [savedItems, setSavedItems] = useState<number[]>([]);

  // 페이지네이션
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);
  const [hasMore, setHasMore] = useState(false);

  const dropdownRef = useRef<HTMLDivElement>(null);

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

  // 사용자 정보 가져오기
  useEffect(() => {
    const token = sessionStorage.getItem("token");
    if (!token) {
      router.push("/start");
      return;
    }

    const storedName = sessionStorage.getItem("userName");
    if (storedName) {
      setUserName(storedName);
    } else {
      getMe().then((res) => {
        if (res.success && res.data.user.name) {
          setUserName(res.data.user.name);
          sessionStorage.setItem("userName", res.data.user.name);
        }
      }).catch((err) => {
        console.error("사용자 정보 조회 실패:", err);
      });
    }
  }, [router]);

  // 좋아요한 코디 목록 가져오기
  const fetchFavorites = async (page: number = 1) => {
    setLoading(true);
    setError("");

    try {
      const response = await getFavorites({ page, limit: 12 });
      setFavorites(response.data.outfits);
      setCurrentPage(page);
      setTotalPages(response.data.pagination.totalPages);
      setHasMore(response.data.pagination.hasNext);
    } catch (err: any) {
      console.error("좋아요 목록 로딩 실패:", err);
      setError("좋아요한 코디를 불러오는데 실패했습니다");
    } finally {
      setLoading(false);
    }
  };

  // 초기 로딩
  useEffect(() => {
    fetchFavorites(1);
  }, []);

  // 좋아요 취소
  const handleUnlike = async (outfitId: number) => {
    try {
      await removeFavorite(outfitId);
      // 목록에서 제거
      setFavorites(favorites.filter((f) => f.id !== outfitId));
    } catch (err: any) {
      console.error("좋아요 취소 실패:", err);
      alert("좋아요 취소에 실패했습니다");
    }
  };

  // 로그아웃
  const handleLogout = async () => {
    try {
      await logout();
      router.push("/start");
    } catch (err) {
      router.push("/start");
    }
  };

  // 페이지 변경
  const handlePageChange = (newPage: number) => {
    if (newPage >= 1 && newPage <= totalPages) {
      fetchFavorites(newPage);
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
  };

  // 옷장에 아이템 저장
  const handleSaveToCloset = async (itemId: number) => {
    if (savedItems.includes(itemId)) {
      alert("이미 옷장에 저장된 아이템입니다");
      return;
    }

    try {
      await saveClosetItem(itemId);
      setSavedItems([...savedItems, itemId]);
      alert("✅ 옷장에 저장되었습니다!");
    } catch (err: any) {
      const errorMessage = err.response?.data?.error?.message || "저장에 실패했습니다";
      alert(errorMessage);
    }
  };

  if (loading && favorites.length === 0) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gradient-to-b from-[rgba(86,151,176,0.45)] via-[rgba(255,244,234,0.65)] to-[rgba(255,244,234,1)]">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-[#5697B0] border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-gray-500">좋아요 목록을 불러오는 중...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-[100dvh] overflow-hidden bg-gradient-to-b from-[rgba(86,151,176,0.45)] via-[rgba(255,244,234,0.65)] to-[rgba(255,244,234,1)] flex flex-col">
      {/* 상단 네비게이션 */}
      <nav className="bg-transparent px-6 pb-4 pt-[calc(1rem+env(safe-area-inset-top))] flex justify-between items-center flex-shrink-0">
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
          <h1 className="hidden md:block text-xl font-bold text-gray-800">좋아요한 코디</h1>

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

      {/* 메인 컨텐츠 */}
      <div className="flex-1 overflow-auto px-6 py-8 pb-[calc(5rem+env(safe-area-inset-bottom))]">
        {error && (
          <div className="text-center mb-6">
            <p className="text-red-500 mb-4">{error}</p>
            <button
              onClick={() => fetchFavorites(currentPage)}
              className="px-6 py-2 bg-[#5697B0] text-white rounded-lg hover:opacity-80"
            >
              다시 시도
            </button>
          </div>
        )}

        {favorites.length > 0 ? (
          <>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6 max-w-7xl mx-auto">
              {favorites.map((outfit) => (
                <div
                  key={outfit.id}
                  className="bg-white rounded-2xl shadow-lg overflow-hidden group hover:shadow-xl transition-shadow cursor-pointer"
                  onClick={() => setSelectedOutfit(outfit)}
                >
                  {/* 코디 이미지 */}
                  <div className="aspect-[3/4] bg-gray-100 relative overflow-hidden">
                    {outfit.imageUrl ? (
                      <img
                        src={outfit.imageUrl}
                        alt={outfit.description || "코디 이미지"}
                        className="w-full h-full object-cover"
                      />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center text-gray-400">
                        <div className="text-center">
                          <p className="text-6xl mb-2">👕</p>
                          <p className="text-sm">{outfit.style} / {outfit.season}</p>
                        </div>
                      </div>
                    )}

                    {/* 좋아요 취소 버튼 */}
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleUnlike(outfit.id);
                      }}
                      className="absolute top-4 right-4 w-10 h-10 md:w-12 md:h-12 rounded-full shadow-lg flex items-center justify-center hover:scale-110 active:scale-95 transition-all duration-300 border bg-pink-50 border-pink-200 text-pink-500"
                    >
                      <HeartIcon
                        filled={true}
                        size={20}
                        className="scale-110"
                      />
                    </button>

                    {/* LLM 메시지 */}
                    {outfit.llmMessage && (
                      <div className="absolute bottom-3 left-3 right-3 bg-white/95 backdrop-blur-sm rounded-lg p-3 shadow-lg border border-gray-100">
                        <p className="text-xs text-gray-700 leading-relaxed">
                          💬 {outfit.llmMessage}
                        </p>
                      </div>
                    )}
                  </div>

                  {/* 코디 정보 */}
                  <div className="p-4">
                    <div className="flex items-center gap-2">
                      <span className="px-2 py-1 bg-[#5697B0]/10 text-[#5697B0] text-xs rounded-full font-medium">
                        {outfit.season}
                      </span>
                      <span className="px-2 py-1 bg-gray-100 text-gray-600 text-xs rounded-full font-medium">
                        {outfit.style}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {/* 페이지네이션 */}
            {totalPages > 1 && (
              <div className="flex justify-center items-center gap-2 mt-8 mb-4">
                <button
                  onClick={() => handlePageChange(currentPage - 1)}
                  disabled={currentPage === 1}
                  className="px-4 py-2 bg-white rounded-lg shadow hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition"
                >
                  ←
                </button>
                <span className="px-4 py-2 bg-white rounded-lg shadow font-medium">
                  {currentPage} / {totalPages}
                </span>
                <button
                  onClick={() => handlePageChange(currentPage + 1)}
                  disabled={!hasMore}
                  className="px-4 py-2 bg-white rounded-lg shadow hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition"
                >
                  →
                </button>
              </div>
            )}
          </>
        ) : (
          <div className="flex flex-col items-center justify-center h-[60vh] text-gray-400">
            <p className="text-8xl mb-6">💔</p>
            <p className="text-xl mb-2 font-medium text-gray-600">아직 좋아요한 코디가 없어요</p>
            <p className="text-sm text-gray-500 mb-6">메인 페이지에서 마음에 드는 코디를 찾아보세요!</p>
            <button
              onClick={() => {
                sessionStorage.setItem("mainPageNavigating", "true");
                router.push("/main");
              }}
              className="px-8 py-3 bg-[#5697B0] text-white rounded-xl font-medium hover:opacity-90 transition shadow-lg"
            >
              코디 둘러보기
            </button>
          </div>
        )}
      </div>

      {/* 코디 상세 모달 */}
      {selectedOutfit && (
        <div
          className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-6"
          onClick={() => setSelectedOutfit(null)}
        >
          <div
            className="bg-white rounded-3xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
            {/* 모달 헤더 */}
            <div className="px-6 py-4 border-b flex justify-between items-center sticky top-0 bg-white z-10">
              <h2 className="text-xl font-bold text-gray-800">코디 상품 정보</h2>
              <button
                onClick={() => setSelectedOutfit(null)}
                className="w-8 h-8 rounded-full hover:bg-gray-100 flex items-center justify-center transition"
              >
                ✕
              </button>
            </div>

            {/* 모달 바디 */}
            <div className="p-6 overflow-y-auto max-h-[calc(90vh-80px)]">
              {/* 상품 목록 */}
              <div>
                <h3 className="text-lg font-bold text-gray-800 mb-3 flex items-center gap-2">
                  <span>Items</span>
                  <span className="text-xs font-normal text-gray-500 bg-gray-100 px-2 py-0.5 rounded-full">
                    {selectedOutfit.items.length}
                  </span>
                </h3>

                <div className="flex flex-col gap-3">
                  {selectedOutfit.items.map((item) => (
                    <div
                      key={item.id}
                      className="bg-white rounded-lg shadow-sm border border-gray-100 p-3 flex gap-3 hover:shadow-md transition-shadow"
                    >
                      {/* 상품 이미지 */}
                      <div className="w-20 h-20 bg-gray-50 rounded-lg flex items-center justify-center flex-shrink-0 overflow-hidden">
                        {item.imageUrl ? (
                          <img
                            src={item.imageUrl}
                            alt={item.name}
                            className="w-full h-full object-cover"
                          />
                        ) : (
                          <span className="text-2xl">👔</span>
                        )}
                      </div>

                      {/* 상품 정보 */}
                      <div className="flex-1 flex flex-col justify-between min-w-0">
                        <div>
                          <p className="text-xs text-gray-400 font-bold tracking-wide">
                            {item.brand || "BRAND"}
                          </p>
                          {item.purchaseUrl ? (
                            <a
                              href={item.purchaseUrl}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="font-medium text-gray-800 text-sm hover:text-[#5697B0] hover:underline cursor-pointer block"
                            >
                              {item.name}
                            </a>
                          ) : (
                            <p className="font-medium text-gray-800 text-sm">
                              {item.name}
                            </p>
                          )}
                          <p className="text-xs text-gray-400 mt-0.5">
                            {item.category}
                          </p>
                        </div>

                        <div className="flex items-center justify-between mt-2">
                          {item.price ? (
                            <p className="text-[#5697B0] font-bold text-sm">
                              {item.price.toLocaleString()}원
                            </p>
                          ) : (
                            <p className="text-gray-400 text-sm">가격 문의</p>
                          )}
                          <button
                            onClick={() => handleSaveToCloset(item.id)}
                            className={`px-3 py-1.5 text-xs rounded-md transition-all font-medium ${savedItems.includes(item.id)
                              ? "bg-gray-800 text-white"
                              : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                              }`}
                          >
                            {savedItems.includes(item.id) ? "Saved ✓" : "Add Closet"}
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}


    </div>
  );
}
