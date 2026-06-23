import { ref } from "vue";

// 영화 검색 페이지 상태 공유 (모듈 싱글톤) — useMarkerMode 와 같은 패턴.
// 상세로 갔다가 뒤로 와도 검색어·필터·결과가 유지되도록 컴포넌트 밖에 보관 (F-MOV-01).
const query = ref("");
const filters = ref({ genre: "", min_rating: "", max_rating: "", decade: "", runtime: "" });
const results = ref([]);
const searched = ref(false); // 검색어/필터로 한 번이라도 조회했는지 (라벨용)
const loaded = ref(false);   // 최초 랜딩(평점 높은순) 로드 여부 — 재진입 시 재조회 방지

function resetFilters() {
  filters.value = { genre: "", min_rating: "", max_rating: "", decade: "", runtime: "" };
}

export function useMovieSearch() {
  return { query, filters, results, searched, loaded, resetFilters };
}
