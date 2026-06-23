import { ref } from "vue";
import { getMe } from "@/api/auth";

// 현재 로그인 사용자 공유 상태 (모듈 싱글톤 ref) — useMarkerMode 와 같은 패턴.
// 우상단 아바타(AppLayout)·프로필 등 여러 곳이 같은 값을 보고,
// 사진/닉네임 변경·삭제 시 setUser 로 즉시 반영(새로고침 불필요).
const user = ref(null); // { pk, email, nickname, profile_image_url, onboarded } | null
let inflight = null;     // 동시 호출 시 중복 요청 방지

async function loadUser(force = false) {
  if (user.value && !force) return user.value;
  if (inflight) return inflight;
  inflight = getMe()
    .then((data) => (user.value = data))
    .catch(() => (user.value = null))
    .finally(() => (inflight = null));
  return inflight;
}

function setUser(data) {
  user.value = data;
}

function clearUser() {
  user.value = null;
}

export function useCurrentUser() {
  return { user, loadUser, setUser, clearUser };
}
