// lib/fitting.ts
// 가상 피팅 관련 API 함수들

import api from "./api";
import type { ApiSuccessResponse, Pagination } from "@/types/api";

/**
 * ============================================
 * 가상 피팅 타입 정의
 * ============================================
 */

export type FittingStatus = "processing" | "completed" | "failed" | "timeout";
export type FittingCategory = "top" | "bottom" | "outer";

export interface FittingItem {
  itemId: number;
  category: FittingCategory;
}

export interface StartFittingRequest {
  items: FittingItem[];
}

export interface FittingJob {
  jobId: number;
  status: FittingStatus;
  createdAt: string;
}

export interface FittingJobStatus {
  jobId: number;
  status: FittingStatus;
  currentStep?: string;
  resultImageUrl?: string;
  llmMessage?: string;
  completedAt?: string;
  processingTime?: number;
  error?: string;
  failedStep?: string;
  failedAt?: string;
  timeoutAt?: string;
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
 * 가상 피팅 시작
 * POST /api/virtual-fitting
 * ============================================
 */
export const startFitting = async (data: StartFittingRequest) => {
  const response = await api.post<ApiSuccessResponse<FittingJob>>(
    "/virtual-fitting",
    data
  );
  return response.data;
};

/**
 * ============================================
 * 가상 피팅 상태 조회
 * GET /api/virtual-fitting/{jobId}
 * ============================================
 */
export const getFittingStatus = async (jobId: number) => {
  const response = await api.get<ApiSuccessResponse<FittingJobStatus>>(
    `/virtual-fitting/${jobId}`
  );
  return response.data;
};

/**
 * ============================================
 * 가상 피팅 상태 폴링
 * 완료/실패/타임아웃까지 2초 간격으로 폴링
 * ============================================
 */
export const pollFittingStatus = async (
  jobId: number,
  maxAttempts: number = 60 // 최대 2분 (2초 x 60)
): Promise<ApiSuccessResponse<FittingJobStatus>> => {
  let attempts = 0;

  while (attempts < maxAttempts) {
    const result = await getFittingStatus(jobId);
    const status = result.data.status;

    // 완료, 실패, 타임아웃 상태면 결과 반환
    if (status === "completed" || status === "failed" || status === "timeout") {
      return result;
    }

    // 2초 대기
    await new Promise((resolve) => setTimeout(resolve, 2000));
    attempts++;
  }

  // 최대 시도 횟수 초과
  throw new Error("피팅 상태 조회 시간 초과");
};

/**
 * ============================================
 * 가상 피팅 이력 조회
 * GET /api/virtual-fitting
 * ============================================
 */
export const getFittingHistory = async (params?: {
  page?: number;
  limit?: number;
}) => {
  const response = await api.get<
    ApiSuccessResponse<{
      fittings: FittingHistoryItem[];
      pagination: Pagination;
    }>
  >("/virtual-fitting", {
    params: {
      page: params?.page || 1,
      limit: params?.limit || 20,
    },
  });
  return response.data;
};

/**
 * ============================================
 * 가상 피팅 이력 삭제
 * DELETE /api/virtual-fitting/{jobId}
 * ============================================
 */
export const deleteFittingHistory = async (jobId: number) => {
  const response = await api.delete<
    ApiSuccessResponse<{
      message: string;
      deletedAt: string;
    }>
  >(`/virtual-fitting/${jobId}`);
  return response.data;
};