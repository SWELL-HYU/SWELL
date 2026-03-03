// 사용자
export interface User {
    id: number;
    email: string;
    name: string;
    gender: "male" | "female";
    profileImageUrl: string | null;
    preferredTags: Tag[] | null;
    preferredCoordis: Coordi[] | null;
    hasCompletedOnboarding: boolean;
    createdAt: string;
  }
  
  // 태그
  export interface Tag {
    id: number;
    name: string;
  }
  
  // 코디
  export interface Coordi {
    id: number;
    style: string;
    season: string;
    gender: string;
    description: string;
    mainImageUrl: string;
  }
  
  // 아이템 (상품)
  export interface Item {
    id: number;
    name: string;
    brand: string;
    category: string;
    price: number;
    imageUrl: string;
    purchaseUrl: string;
  }
  
  // API 응답 공통 형식
  export interface ApiResponse<T> {
    success: boolean;
    data?: T;
    message?: string;
    error?: {
      code: string;
      message: string;
    };
  }
  
  // 페이지네이션
  export interface Pagination {
    currentPage: number;
    totalPages: number;
    totalItems: number;
    hasNext: boolean;
    hasPrev: boolean;
  }