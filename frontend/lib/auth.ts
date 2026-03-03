// lib/auth.ts
// 인증 관련 API 함수들 (API 명세서 ver 3.0 기반)

import api from "./api";
import type {
  ApiSuccessResponse,
  User,
  SignupRequest,
  LoginRequest,
} from "@/types/api";

/**
 * ============================================
 * 1.1 회원가입
 * POST /api/auth/signup
 * ============================================
 */
export const signup = async (data: SignupRequest) => {
  const response = await api.post<
    ApiSuccessResponse<{
      user: User;
    }>
  >("/auth/signup", data);
  return response.data;
};

/**
 * ============================================
 * 1.2 로그인
 * POST /api/auth/login
 * ============================================
 */
export const login = async (data: LoginRequest) => {
  const response = await api.post<
    ApiSuccessResponse<{
      user: User;
      token: string;
    }>
  >("/auth/login", data);

  // 로그인 성공 시 토큰 및 사용자 정보 저장
  if (response.data.success && response.data.data.token) {
    if (typeof window !== "undefined") {
      sessionStorage.setItem("token", response.data.data.token);
      sessionStorage.setItem("userName", response.data.data.user.name);
    }
  }

  return response.data;
};

/**
 * ============================================
 * 1.3 로그아웃
 * POST /api/auth/logout
 * ============================================
 */
export const logout = async () => {
  const response = await api.post<
    ApiSuccessResponse<{
      message: string;
    }>
  >("/auth/logout");

  // 로그아웃 성공 시 토큰 및 사용자 정보 삭제
  if (response.data.success) {
    if (typeof window !== "undefined") {
      sessionStorage.removeItem("token");
      sessionStorage.removeItem("userName");
    }
  }

  return response.data;
};

/**
 * ============================================
 * 1.4 내 정보 조회
 * GET /api/auth/me
 * ============================================
 */
export const getMe = async (): Promise<ApiSuccessResponse<{ user: User }>> => {
  const response = await api.get<
    ApiSuccessResponse<{
      user: User;
    }>
  >("/auth/me");
  return response.data;
};

/**
 * ============================================
 * 유틸리티 함수
 * ============================================
 */

// 로그인 여부 확인
export const isAuthenticated = (): boolean => {
  if (typeof window === "undefined") return false;
  return !!sessionStorage.getItem("token");
};

// 토큰 가져오기
export const getToken = (): string | null => {
  if (typeof window === "undefined") return null;
  return sessionStorage.getItem("token");
};

// 토큰 삭제 (강제 로그아웃)
export const clearToken = (): void => {
  if (typeof window !== "undefined") {
    sessionStorage.removeItem("token");
  }
};