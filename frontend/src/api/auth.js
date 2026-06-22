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

// 온보딩 완료 여부 캐시 (null=미조회). 가드가 매 이동마다 API 안 치도록.
let onboardedCache = null;
export function setOnboarded(v) {
  onboardedCache = v;
}
export async function fetchOnboarded() {
  if (onboardedCache !== null) return onboardedCache;
  try {
    const { data } = await api.get("/auth/user/");
    onboardedCache = !!data.onboarded;
  } catch {
    onboardedCache = false;
  }
  return onboardedCache;
}

// 로그인 → 토큰 저장 (다음 유저 위해 온보딩 캐시 초기화)
export async function login(email, password) {
  const { data } = await api.post("/auth/login/", { email, password });
  setToken(data.key);
  onboardedCache = null;
  return data;
}

// 회원가입 → 가입 즉시 토큰 발급(로그인 상태로 전환). 신규 유저는 온보딩 미완.
export async function register({ email, password1, password2, nickname }) {
  const { data } = await api.post("/auth/registration/", {
    email,
    password1,
    password2,
    nickname,
  });
  setToken(data.key);
  onboardedCache = false;
  return data;
}

// 온보딩 완료 처리 (백엔드가 시청 5편 검증) → 캐시 갱신
export async function completeOnboarding() {
  await api.post("/accounts/onboarding/complete/");
  onboardedCache = true;
}

// 내 프로필 조회 (F-AUTH-04) → { pk, email, nickname, profile_image_url, onboarded }
export async function getMe() {
  const { data } = await api.get("/auth/user/");
  return data;
}

// 프로필 수정 (닉네임 + 선택 사진파일). 사진 있으면 multipart, 없으면 JSON.
export async function updateProfile({ nickname, imageFile }) {
  if (imageFile) {
    const fd = new FormData();
    if (nickname != null) fd.append("nickname", nickname);
    fd.append("profile_image", imageFile);
    const { data } = await api.patch("/auth/user/", fd);
    return data;
  }
  const { data } = await api.patch("/auth/user/", { nickname });
  return data;
}

// 비밀번호 변경 (F-AUTH-04) — 현재 비밀번호 확인(OLD_PASSWORD_FIELD_ENABLED) 포함
export async function changePassword({ old_password, new_password1, new_password2 }) {
  await api.post("/auth/password/change/", { old_password, new_password1, new_password2 });
}

// 계정 삭제 (F-AUTH-05, Hard). 성공 시 토큰·캐시 정리.
export async function deleteAccount() {
  await api.delete("/accounts/me/");
  clearToken();
  onboardedCache = null;
}

// 로그아웃 = 서버 토큰 폐기 + 클라이언트 토큰 삭제 + 캐시 초기화
export async function logout() {
  try {
    await api.post("/auth/logout/");
  } finally {
    clearToken();
    onboardedCache = null;
  }
}
