// types/api.ts
// API 명세서 기반 TypeScript 타입 정의

/**
 * ============================================
 * 공통 응답 타입
 * ============================================
 */

// 성공 응답
export interface ApiSuccessResponse<T = any> {
  success: true;
  data: T;
  message?: string;
}

// 에러 응답
export interface ApiErrorResponse {
  success: false;
  error: {
    code: string;
    message: string;
  };
}

// API 응답 (성공 또는 에러)
export type ApiResponse<T = any> = ApiSuccessResponse<T> | ApiErrorResponse;

/**
 * ============================================
 * 페이지네이션
 * ============================================
 */

export interface Pagination {
  currentPage: number;
  totalPages: number;
  totalItems: number;
  hasNext: boolean;
  hasPrev: boolean;
}

/**
 * ============================================
 * 사용자 관련 타입
 * ============================================
 */

export type Gender = "male" | "female";

export interface User {
  id: number;
  email: string;
  name: string;
  gender: Gender;
  profileImageUrl: string | null;
  preferredTags: Tag[] | null;
  preferredCoordis: number[] | null;
  hasCompletedOnboarding: boolean;
  createdAt: string; // ISO 8601
}

/**
 * ============================================
 * 태그 관련 타입
 * ============================================
 */

export interface Tag {
  id: number;
  name: string;
}

/**
 * ============================================
 * 코디(Outfit) 관련 타입
 * ============================================
 */

export type Season = "spring" | "summer" | "fall" | "winter";
export type Style = "casual" | "street" | "sporty" | "minimal";

export interface OutfitItem {
  id: number;
  category: string;
  name: string;
  brand: string | null;
  price: number | null;
  imageUrl: string;
  purchaseUrl: string | null;
}

export interface Outfit {
  id: number;
  style: Style;
  season: Season;
  gender: Gender;
  imageUrl: string;
  description: string | null;
  items: OutfitItem[];
  isFavorite: boolean;
  createdAt: string;
  llmMessage?: string | null; // LLM 추천 메시지
}

/**
 * ============================================
 * 옷장(Closet) 관련 타입 (백엔드 스키마 기반)
 * ============================================
 */

export interface ClosetItem {
  id: number;
  category: string;
  brand: string | null;
  name: string;
  price: number | null;
  imageUrl: string | null;
  purchaseUrl: string | null;
  savedAt: string;
}

export interface CategoryCounts {
  top: number;
  bottom: number;
  outer: number;
}

/**
 * ============================================
 * 가상 피팅 관련 타입
 * ============================================
 */

export type FittingStatus = "processing" | "completed" | "failed" | "timeout";

export interface FittingJob {
  jobId: number;
  status: FittingStatus;
  resultImageUrl?: string | null;
  currentStep?: string;
  failedStep?: string;
  createdAt: string;
}

export interface FittingHistoryItem {
  jobId: number;
  status: FittingStatus;
  resultImageUrl: string | null;
  items: {
    itemId: number;
    category: string;
    name: string;
  }[];
  createdAt: string;
}

/**
 * ============================================
 * 요청 바디 타입
 * ============================================
 */

// 회원가입
export interface SignupRequest {
  email: string;
  password: string;
  name: string;
  gender: Gender;
}

// 로그인
export interface LoginRequest {
  email: string;
  password: string;
}

// 온보딩 설문
export interface OnboardingRequest {
  preferredTags: number[]; // 태그 ID 배열 (최소 3개)
  preferredCoordis: number[]; // 코디 ID 배열 (정확히 5개)
}

// 옷장에 옷 추가 (실제로는 사용 안 함 - 아이템 ID만 저장)
export interface AddClosetItemRequest {
  image: File;
  season: Season;
}

// 가상 피팅 시작
export interface StartFittingRequest {
  itemIds: number[]; // 옷장 아이템 ID 배열
}

// 프로필 수정
export interface UpdateProfileRequest {
  name?: string;
  gender?: Gender;
  preferredTags?: number[];
}