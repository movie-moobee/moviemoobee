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

// OTT·예고편 (TMDB watch providers + trailer)
export async function getMovieExtras(id) {
  const { data } = await api.get(`/movies/${id}/extras/`);
  return data; // { ott: [{name, logo}], trailer: "<youtubeKey>"|null }
}
