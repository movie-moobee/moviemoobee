import { api } from "./client";

// 취향 지도·추천 API (F-MAP·F-REC) → /api/taste/

// 취향 지도: 본 영화 마커(좌표·밝기=KDE)·내 좌표 (F-MAP-01)
export async function getMyMap() {
  const { data } = await api.get("/taste/me/map");
  return data; // { enough, user_coord, watched:[{movie_id,title,poster_path,x,y,rating,brightness}] }
}

// 추천: 안전(본 영화 kNN 근접)·미탐색(KDE 저밀도) 각 10편 (F-REC, 4.1/4.2/4.3)
export async function getRecommendations() {
  const { data } = await api.get("/taste/recommendations");
  return data; // { enough, user_coord, safe:[{id,title,release_year,poster_path,vote_average,distance}], unexplored:[{...,density}] }
}
