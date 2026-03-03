// lib/onboarding.ts
// 온보딩 관련 API 함수들

import api from "./api";
import type { ApiSuccessResponse } from "@/types/api";

/**
 * ============================================
 * 온보딩 타입 정의
 * ============================================
 */

export interface Tag {
  id: number;
  name: string;
}

export interface SampleOutfit {
  id: number;
  imageUrl: string;
  style: string;
  season: string;
}

export interface PreferenceOptions {
  hashtags: Tag[];
  sampleOutfits: SampleOutfit[];
}

export interface SetPreferencesRequest {
  hashtagIds: number[];
  sampleOutfitIds: number[];
}

/**
 * ============================================
 * 선호도 설정 옵션 조회
 * GET /api/users/preferences/options
 * ============================================
 */
export const getPreferenceOptions = async () => {
  const response = await api.get<
    ApiSuccessResponse<PreferenceOptions>
  >("/users/preferences/options");
  return response.data;
};

/**
 * ============================================
 * 선호도 설정 (온보딩 완료)
 * POST /api/users/preferences
 * ============================================
 */
export const setPreferences = async (data: SetPreferencesRequest) => {
  const response = await api.post<
    ApiSuccessResponse<{
      message: string;
      user: {
        id: number;
        hasCompletedOnboarding: boolean;
      };
    }>
  >("/users/preferences", data);
  return response.data;
};