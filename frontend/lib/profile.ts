// lib/profile.ts
// 프로필 사진 관련 API 함수들

import api from "./api";
import type { ApiSuccessResponse } from "@/types/api";

/**
 * ============================================
 * 프로필 사진 업로드
 * POST /api/users/profile-photo
 * ============================================
 */
export const uploadProfilePhoto = async (file: File) => {
  const formData = new FormData();
  formData.append("photo", file);

  const response = await api.post<
    ApiSuccessResponse<{
      photoUrl: string;
      createdAt: string;
    }>
  >("/users/profile-photo", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });
  return response.data;
};

/**
 * ============================================
 * 프로필 사진 삭제
 * DELETE /api/users/profile-photo
 * ============================================
 */
export const deleteProfilePhoto = async () => {
  const response = await api.delete<
    ApiSuccessResponse<{
      message: string;
      deletedAt: string;
    }>
  >("/users/profile-photo");
  return response.data;
};