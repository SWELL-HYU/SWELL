// lib/outfits.ts
// 코디 추천 및 조회 관련 API 함수들

import api from "./api";
import type {
  ApiSuccessResponse,
  Outfit,
  Pagination,
} from "@/types/api";

/**
 * ============================================
 * 개인화 추천 코디 목록
 * GET /api/recommendations
 * ============================================
 */
export const getRecommendations = async (params?: {
  page?: number;
  limit?: number;
}) => {
  const response = await api.get<ApiSuccessResponse<{
    outfits: Outfit[];
    pagination: Pagination;
  }>>("/recommendations", {
    params: {
      page: params?.page || 1,
      limit: params?.limit || 20,
    },
  });
  return response.data;
};

/**
 * ============================================
 * 특정 코디 상세 조회
 * GET /api/outfits/{outfitId}
 * ============================================
 */
export const getOutfitDetail = async (outfitId: number) => {
  const response = await api.get<ApiSuccessResponse<{
    outfit: Outfit;
  }>>(`/outfits/${outfitId}`);
  return response.data;
};

/**
 * ============================================
 * 코디에 좋아요 추가
 * POST /api/outfits/{outfitId}/favorite
 * ============================================
 */
export const addFavorite = async (outfitId: number) => {
  const response = await api.post<ApiSuccessResponse<{
    outfitId: number;
    isFavorited: boolean;
    favoritedAt: string;
  }>>(`/outfits/${outfitId}/favorite`);
  return response.data;
};

/**
 * ============================================
 * 코디 좋아요 취소
 * DELETE /api/outfits/{outfitId}/favorite
 * ============================================
 */
export const removeFavorite = async (outfitId: number) => {
  const response = await api.delete<ApiSuccessResponse<{
    outfitId: number;
    isFavorited: boolean;
    unfavoritedAt: string;
  }>>(`/outfits/${outfitId}/favorite`);
  return response.data;
};

/**
 * ============================================
 * 좋아요한 코디 목록
 * GET /api/outfits/favorites
 * ============================================
 */
export const getFavorites = async (params?: {
  page?: number;
  limit?: number;
}) => {
  const response = await api.get<ApiSuccessResponse<{
    outfits: Outfit[];
    pagination: Pagination;
  }>>("/outfits/favorites", {
    params: {
      page: params?.page || 1,
      limit: params?.limit || 20,
    },
  });
  return response.data;
};

/**
 * ============================================
 * 코디 스킵
 * POST /api/outfits/{outfitId}/skip
 * ============================================
 */
export const skipOutfit = async (outfitId: number) => {
  const response = await api.post<ApiSuccessResponse<{
    outfitId: number;
    isSkipped: boolean;
    skippedAt: string;
  }>>(`/outfits/${outfitId}/skip`);
  return response.data;
};

/**
 * ============================================
 * 코디 조회 로그 기록
 * POST /api/outfits/{outfitId}/view
 * ============================================
 */
export const recordViewLog = async (outfitId: number, durationSeconds: number) => {
  const response = await api.post<ApiSuccessResponse<{
    message: string;
    recordedAt: string;
  }>>(`/outfits/${outfitId}/view`, {
    durationSeconds,
  });
  return response.data;
};
