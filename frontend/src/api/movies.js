import { api } from "./client";

// 영화 API (F-MOV-01·02·03) → /api/movies/

// 검색 (제목)
export async function searchMovies(query) {
  const { data } = await api.get("/movies/", { params: { search: query } });
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
