import { api } from "./client";

// 인증 API · 토큰 헬퍼 (F-AUTH-01·02·03)
const TOKEN_KEY = "token";

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}
export function setToken(key) {
  localStorage.setItem(TOKEN_KEY, key);
}
export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}
export function isAuthenticated() {
  return !!getToken();
}

// 로그인 → 토큰 저장
export async function login(email, password) {
  const { data } = await api.post("/auth/login/", { email, password });
  setToken(data.key);
  return data;
}

// 회원가입 → 가입 즉시 토큰 발급(로그인 상태로 전환)
export async function register({ email, password1, password2, nickname }) {
  const { data } = await api.post("/auth/registration/", {
    email,
    password1,
    password2,
    nickname,
  });
  setToken(data.key);
  return data;
}

// 로그아웃 = 서버 토큰 폐기 + 클라이언트 토큰 삭제
export async function logout() {
  try {
    await api.post("/auth/logout/");
  } finally {
    clearToken();
  }
}
