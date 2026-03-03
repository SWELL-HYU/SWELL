// lib/closet.ts
// 옷장 관리 관련 API 함수들 (완전 버전)

import api from "./api";
import type {
  ApiSuccessResponse,
  Pagination,
} from "@/types/api";

/**
 * ============================================
 * 옷장 아이템 타입 (백엔드 스키마 기반)
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
 * 옷장 아이템 목록 조회
 * GET /api/closet
 * ============================================
 */
export const getClosetItems = async (params?: {
  page?: number;
  limit?: number;
  category?: "all" | "top" | "bottom" | "outer";
}) => {
  const response = await api.get<
    ApiSuccessResponse<{
      items: ClosetItem[];
      pagination: Pagination;
      categoryCounts: CategoryCounts;
    }>
  >("/closet", {
    params: {
      page: params?.page || 1,
      limit: params?.limit || 20,
      category: params?.category || "all",
    },
  });
  return response.data;
};

/**
 * ============================================
 * 옷장에 아이템 저장
 * POST /api/closet/items
 * ============================================
 */
export const saveClosetItem = async (itemId: number) => {
  const response = await api.post<
    ApiSuccessResponse<{
      message: string;
      savedAt: string;
    }>
  >("/closet/items", { itemId });
  return response.data;
};

/**
 * ============================================
 * 옷장에서 아이템 삭제
 * DELETE /api/closet/items/{itemId}
 * ============================================
 */
export const deleteClosetItem = async (itemId: number) => {
  const response = await api.delete<
    ApiSuccessResponse<{
      message: string;
      deletedAt: string;
    }>
  >(`/closet/items/${itemId}`);
  return response.data;
};