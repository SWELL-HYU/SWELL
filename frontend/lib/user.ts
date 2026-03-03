import api from "./api";
import { ApiResponse, Tag, Coordi } from "@/types";

// Cold-start 설문 제출
export async function submitOnboarding(data: {
  tagIds: number[];
  coordiIds: number[];
}): Promise<ApiResponse<null>> {
  const response = await api.post("/users/onboarding", data);
  return response.data;
}

// 프로필 사진 업로드
export async function uploadProfileImage(
  file: File
): Promise<ApiResponse<{ profileImageUrl: string }>> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await api.post("/users/profile-image", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data;
}

// 온보딩용 태그 목록 조회
export async function getOnboardingTags(): Promise<ApiResponse<{ tags: Tag[] }>> {
  const response = await api.get("/users/onboarding/tags");
  return response.data;
}

// 온보딩용 코디 목록 조회
export async function getOnboardingCoordis(): Promise<ApiResponse<{ coordis: Coordi[] }>> {
  const response = await api.get("/users/onboarding/coordis");
  return response.data;
}