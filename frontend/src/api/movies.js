import { api } from "./client";

// 영화 API (F-MOV-01·02·03) → /api/movies/

// 검색 (제목) — 지도 등록 탭 등 단순 호출용
export async function searchMovies(query) {
  const { data } = await api.get("/movies/", { params: { search: query } });
  return data;
}

// 검색 페이지: 검색어 + 필터(genre·min_rating·decade·runtime·language). 빈 값은 제외.
export async function browseMovies(params = {}) {
  const clean = {};
  for (const [k, v] of Object.entries(params)) {
    if (v !== "" && v != null) clean[k] = v;
  }
  const { data } = await api.get("/movies/", { params: clean });
  return data;
}

// 장르 드롭다운 옵션 (카탈로그에 영화 있는 장르명)
export async function getGenres() {
  const { data } = await api.get("/movies/genres/");
  return data;
}

// 최근 추가된 영화 (메인 가로 스크롤, created_at 신규순)
export async function getRecentMovies(limit = 12) {
  const { data } = await api.get("/movies/", { params: { sort: "recent", limit } });
  return data;
}

// 상세 (제목·장르·키워드·감독·줄거리·평점 등)
export async function getMovie(id) {
  const { data } = await api.get(`/movies/${id}/`);
  return data;
}

// OTT (TMDB watch providers, 서버 6시간 캐싱). 예고편은 상세 응답의 trailer_key로 분리.
export async function getMovieExtras(id) {
  const { data } = await api.get(`/movies/${id}/extras/`);
  return data; // { ott: [{name, logo}] }
}

// 이용자 리뷰 (전 유저, 리뷰 있는 것만 최신순) — F-MOV-04
export async function getMovieReviews(id) {
  const { data } = await api.get(`/movies/${id}/reviews/`);
  return data.results ?? data; // 나중에 페이지네이션 붙어도 안 깨지게 results 우선
}
