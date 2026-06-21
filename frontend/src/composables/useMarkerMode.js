import { ref, watch } from "vue";

// 지도 마커 모드(별/포스터) 공유 상태 — 홈·지도 페이지가 같은 값을 본다(모듈 싱글톤 ref).
// localStorage에 지속 → 새로고침에도 유지. /map에선 ?view= 와도 동기화(deep-link).
const KEY = "mm_marker_mode";
const stored = typeof localStorage !== "undefined" ? localStorage.getItem(KEY) : null;
const markerMode = ref(stored === "posters" ? "posters" : "stars");

watch(markerMode, (v) => {
  try { localStorage.setItem(KEY, v); } catch { /* 무시 */ }
});

export function useMarkerMode() {
  return markerMode;
}
