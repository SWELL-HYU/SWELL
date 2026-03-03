import axios from "axios";

// 브라우저는 이제 백엔드의 진짜 IP를 알 필요가 없으며, 오직 "자신(프론트)의 /api"로만 요청을 보냅니다.
export const API_BASE_URL = "";

// 🔍 브라우저 콘솔에서도 더 이상 민감한 외부 백엔드 IP가 노출되지 않습니다.
console.log("🌐 API Routing via Reverse Proxy");

// API 기본 설정
const api = axios.create({
  baseURL: `${API_BASE_URL}/api`,
  headers: {
    "Content-Type": "application/json",
  },
});

// 요청할 때마다 토큰 자동 첨부
api.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = sessionStorage.getItem("token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

// 토큰 만료 시 로그인 페이지로 이동
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      if (typeof window !== "undefined") {
        sessionStorage.removeItem("token");
        window.location.href = "/start";
      }
    }
    return Promise.reject(error);
  }
);

export default api;