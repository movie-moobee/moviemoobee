import axios from "axios";

// 로컬: Vite 프록시로 "/api" → :8000. 배포(다른 도메인): VITE_API_URL 로 백엔드 주소 지정.
// SSE(fetch) 쪽도 같은 베이스를 쓰도록 export.
export const API_BASE = import.meta.env.VITE_API_URL || "/api";

export const api = axios.create({ baseURL: API_BASE });

// 요청마다 토큰 자동 첨부 (09_tech_notes 1.3: Authorization: Token <key>)
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) {
    config.headers.Authorization = `Token ${token}`;
  }
  return config;
});

// 토큰 만료·무효 시 자동 로그아웃 처리
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem("token");
      if (window.location.pathname !== "/login") {
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  },
);
