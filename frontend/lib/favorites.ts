import api from "./api";
import { ApiResponse, Coordi, Pagination } from "@/types";

// 좋아요 목록 조회
export async function getFavorites(params?: {
  page?: number;
  limit?: number;
}): Promise<ApiResponse<{ favorites: Coordi[]; pagination: Pagination }>> {
  const response = await api.get("/favorites", { params });
  return response.data;
}

// 좋아요 추가
export async function addFavorite(
  outfitId: number
): Promise<ApiResponse<null>> {
  const response = await api.post(`/favorites/${outfitId}`);
  return response.data;
}

// 좋아요 취소
export async function removeFavorite(
  outfitId: number
): Promise<ApiResponse<null>> {
  const response = await api.delete(`/favorites/${outfitId}`);
  return response.data;
}